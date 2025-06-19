import pandas as pd
import os
from gurobipy import Model, GRB, quicksum


for var_demanda in [1.2, 1.5]:
    def os_join(path):
        return os.path.join("data", path)

    # Definimos los parámetros
    data = {}
    data['upsilon_c'] = pd.read_csv(os_join('comisarias.csv'), usecols=['total_patrullas_por_comisaria']).squeeze().values
    data['pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_min']).squeeze().values
    data['Pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_max']).squeeze().values
    data['K'] = pd.read_csv(os_join('costos.csv'), usecols=['costo_fijo']).squeeze()
    data['k'] = pd.read_csv(os_join('costos.csv'), usecols=['costo_por_hora']).squeeze()
    data['rho_c'] = pd.read_csv(os_join('comisarias.csv'), usecols=['presupuesto_diario_comisaria']).squeeze().values
    data['theta_{q,h}'] = pd.read_csv(os_join('crimenes_por_hora.csv'), header=0, index_col=0).values
    data['a1'] = pd.read_csv(os_join('ponderadores_fo.csv'), usecols=['a1']).squeeze()
    data['a2'] = pd.read_csv(os_join('ponderadores_fo.csv'), usecols=['a2']).squeeze()
    Big_M = 10000000000  



    c_vecinos = pd.read_csv(os_join('cuadrantes_vecinos.csv'), header=None)
    comisarias = pd.read_csv(os_join('cuadrantes.csv'))
    patrullas = pd.read_csv(os_join('patrullas.csv'))
    data['cuadrantes'] = pd.read_csv(os_join('cuadrantes.csv')).squeeze().values
    data['comisarias'] = pd.read_csv(os_join('comisarias.csv')).squeeze().values           
    data['patrullas'] = pd.read_csv(os_join('patrullas.csv')).squeeze().values

    # Creamos conjuntos
    Q = range(1, len(data["cuadrantes"]) + 1) # Conjunto de cuadrantes
    C = range(1, len(data["comisarias"]) + 1) # Conjunto de comisarías
    T = range(1 ,len(data['patrullas']) + 1) # Conjunto de patrullas
    H = range(0, 24) # Conjunto de horas {1, 2, ..., 24}
    J = comisarias.groupby('id_comisaría_asociada')['id_cuadrante'].apply(list).to_dict() # Subconjunto de cuadrantes asignados a cada comisaría
    O = patrullas.groupby('id_comisaría_asignada')['id_patrulla'].apply(list).to_dict() # Subconjunto de cuadrantes asignados a cada comisaría
    V = {}

    for i, fila in c_vecinos.iterrows():
        vecinos = []
        for j, num in enumerate(fila):
            if num != '-':
                vecinos.append(int(num))  # o int(val) si el número que aparece es el id del vecino
        V[i+1] = vecinos

    demanda_hora = round(pd.read_csv(os_join('demanda_cuadrante_hora.csv'), header=None) * var_demanda)
    delta = {}
    for i, fila in demanda_hora.iterrows():
        demanda = []
        for j in fila:
            demanda.append(j) 
        delta[i+1] = demanda


    # Definimos el modelo
    m = Model("Modelo de Optimización de Patrullas")


    # Definimos las variables de decisión       
    y = m.addVars(Q, H, vtype=GRB.BINARY, name="y")  # 1 si se cumple la demanda en el cuadrante *q*, 0 e.o.c. 
    z = m.addVars(Q, H, vtype=GRB.BINARY, name="z")  # 1 si al momento de haber un crimen a la hora *h* en el cuadrante *q*, existe una patrulla en el mismo cuadrante a la misma hora, 0 e.o.c.
    w = m.addVars(((c, t, q, h) for c in C for t in O[c] for q in J[c] for h in H), vtype=GRB.BINARY, name="w")  # 1 si la patrulla *t¨* de la comisaría *c* está en el cuadrante *q* a la hora *h*, 0 e.o.c.
    s = m.addVars(((c, t, h) for c in C for t in O[c] for h in H), vtype=GRB.BINARY, name="s") # 1 si la patrulla *t* de la comisaría *c* sale a la hora *h*, 0 e.o.c.


    # Definimos las restricciones

    # R1: Stock máximo de patrullas por comisaría
    R1 = m.addConstrs(
        (quicksum(s[c, t, h] for t in O[c] for h in H) <= data['upsilon_c'][c-1] for c in C),
        name="R1"
    )

    # R2: Límite de horas de patrullas por comisaría
    R2 = m.addConstrs(
        (quicksum(w[c, t, q, h] for q in J[c] for h in H) <= data['Pi_c'][t-1] for c in C for t in O[c]),
        name="R2"
    )

    # R3: Restricción de presupuesto    
    R3 = m.addConstrs(
        (quicksum(quicksum(data['K'] * s[c, t, h] + quicksum(w[c, t, q, h] * data['k'] 
        for q in J[c]) for h in H) for t in O[c]) <= data['rho_c'][c-1] for c in C for h in H
        ),
        name="R3"
    )

    # R4: Una patrulla solo puede estar en un cuadrante a la vez
    R4 = m.addConstrs(
        (quicksum(w[c, t, q, h] for q in J[c]) <= 1 for c in C for t in O[c] for h in H),
        name="R5"
    )

    # R5: Se visitan todos los cuadrantes al menos una hora al día
    R5 = m.addConstrs(
    (quicksum(w.get((c, t, q, h), 0) for t in O[c] for h in H) >= 1
        for c in C for q in J[c]),
    name="R5"
    )

    # R6: Una patrulla solo puede salir una vez al día
    R6 = m.addConstrs(
        (quicksum(s[c, t, h] for h in H) <= 1 for c in C for t in O[c]), 
        name="R6"
    )

    # R7 No se puede patrullar si no se sale de la comisaría
    R7 = m.addConstrs(
        (quicksum(w[c, t, q, h] for q in J[c] for h in H) <= quicksum(s[c, t, h] for h in H) * Big_M  for c in C for t in O[c] for h in H),
        name="R7"
    )

    # R8: Activación de Y si y solo si se cumple la demanda
    R8 = m.addConstrs(
        (quicksum(w[c, t, q, h] for t in O[c]) >= y[q, h] * delta[q][h-1] for c in C for q in J[c] for h in H),
        name="R8"
    )

    # R9: Activación de Z si y solo si al momento de haber un crimen a la hora *h* en el cuadrante *q*, existe una patrulla en el mismo cuadrante a la misma hora
    R9 = m.addConstrs(
        (z[q, h] <= w[c, t, q, h] * data['theta_{q,h}'][q-1][h-1] for c in C for t in O[c] for q in J[c] for h in H),
        name="R9"
    )

    # R10: Movimiento entre cuadrantes vecinos
    for c in C:
        for t in O[c]:
            for q in J[c]:
                for h in H[:-1]: 
                    no_vecinos = [q_p for q_p in J[c] if q_p not in V[q] and q_p != q] 
                    if no_vecinos:
                        m.addConstr(
                            w[c, t, q, h] + quicksum(w[c, t, q_p, h+1] for q_p in no_vecinos) <= 1,
                            name="R10")

    # R11: Una patrulla no puede estar más de *1* hora en un cuadrante
    R11 = m.addConstrs(
        (w[c, t, q, h] + w[c, t, q, h+1] <= 1 for c in C for t in O[c] for q in J[c] for h in H[:-1]), 
        name="R11"
    )

    '''
    # R11*: Una patrulla no puede estar más de *MAX_HORAS_SEGUIDAS* horas seguidas en un cuadrante
    MAX_HORAS_SEGUIDAS = 2  ### Definir en parámetros??
    for c in C:
        for t in O[c]:
            for q in J[c]:
                for h in range(1, 23 - MAX_HORAS_SEGUIDAS + 2):  # Asegura que no nos pasemos del rango
                    m.addConstr(
                        quicksum(w[c, t, q, h + offset] for offset in range(MAX_HORAS_SEGUIDAS + 1)) <= MAX_HORAS_SEGUIDAS,
                        name=R11)
    '''

    # R12: Restricción de salida de patrullas
    for c in C:
        for t in O[c]:
            for h in H:
                if h == 0:
                    m.addConstr(
                        s[c, t, h] >= quicksum(w[c, t, q, h] for q in J[c]),
                        name=f"R_salida_inicio_c{c}_t{t}_h{h}"
                    )
                else:
                    m.addConstr(
                        s[c, t, h] >= quicksum(w[c, t, q, h] for q in J[c]) - quicksum(w[c, t, q, h - 1] for q in J[c]),
                        name=f"R_salida_cambio_c{c}_t{t}_h{h}"
                    )


    # Definimos la función objetivo
    m.setObjective(
        quicksum(data['a1'] * y[q, h] + data['a2'] * z[q, h] for h in H for q in Q),
        GRB.MAXIMIZE
    )

    # Analisis de sensibilidad
    def resolver_sensibilidad(cambio):
        
        m.optimize()
        if m.status == GRB.OPTIMAL:
            print(cambio)
            print('-' * 80)
            print(f"\nSolución óptima encontrada en {round(m.runtime, 2)}s: {int(m.ObjVal)} unidades de felicidad\n")
            print('-' * 80)

        return None

    resolver_sensibilidad(f"Analisis al variar {var_demanda-1}% la demanda")

for porcentaje in [0.6, 0.8, 1.5, 2]: ### No cambia
    def os_join(path):
        return os.path.join("data", path)

    # Definimos los parámetros
    data = {}
    data['upsilon_c'] = pd.read_csv(os_join('comisarias.csv'), usecols=['total_patrullas_por_comisaria']).squeeze().values
    data['pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_min']).squeeze().values
    data['Pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_max']).squeeze().values
    data['K'] = pd.read_csv(os_join('costos.csv'), usecols=['costo_fijo']).squeeze()
    data['k'] = pd.read_csv(os_join('costos.csv'), usecols=['costo_por_hora']).squeeze()
    data['rho_c'] = pd.read_csv(os_join('comisarias.csv'), usecols=['presupuesto_diario_comisaria']).squeeze().values * porcentaje
    data['theta_{q,h}'] = pd.read_csv(os_join('crimenes_por_hora.csv'), header=0, index_col=0).values
    data['a1'] = pd.read_csv(os_join('ponderadores_fo.csv'), usecols=['a1']).squeeze()
    data['a2'] = pd.read_csv(os_join('ponderadores_fo.csv'), usecols=['a2']).squeeze()
    Big_M = 10000000000  


    c_vecinos = pd.read_csv(os_join('cuadrantes_vecinos.csv'), header=None)
    comisarias = pd.read_csv(os_join('cuadrantes.csv'))
    patrullas = pd.read_csv(os_join('patrullas.csv'))
    data['cuadrantes'] = pd.read_csv(os_join('cuadrantes.csv')).squeeze().values
    data['comisarias'] = pd.read_csv(os_join('comisarias.csv')).squeeze().values           
    data['patrullas'] = pd.read_csv(os_join('patrullas.csv')).squeeze().values

    # Creamos conjuntos
    Q = range(1, len(data["cuadrantes"]) + 1) # Conjunto de cuadrantes
    C = range(1, len(data["comisarias"]) + 1) # Conjunto de comisarías
    T = range(1 ,len(data['patrullas']) + 1) # Conjunto de patrullas
    H = range(0, 24) # Conjunto de horas {1, 2, ..., 24}
    J = comisarias.groupby('id_comisaría_asociada')['id_cuadrante'].apply(list).to_dict() # Subconjunto de cuadrantes asignados a cada comisaría
    O = patrullas.groupby('id_comisaría_asignada')['id_patrulla'].apply(list).to_dict() # Subconjunto de cuadrantes asignados a cada comisaría
    V = {}

    for i, fila in c_vecinos.iterrows():
        vecinos = []
        for j, num in enumerate(fila):
            if num != '-':
                vecinos.append(int(num))  # o int(val) si el número que aparece es el id del vecino
        V[i+1] = vecinos

    demanda_hora = pd.read_csv(os_join('demanda_cuadrante_hora.csv'), header=None)
    delta = {}
    for i, fila in demanda_hora.iterrows():
        demanda = []
        for j in fila:
            demanda.append(j) 
        delta[i+1] = demanda


    # Definimos el modelo
    m = Model("Modelo de Optimización de Patrullas")


    # Definimos las variables de decisión       
    y = m.addVars(Q, H, vtype=GRB.BINARY, name="y")  # 1 si se cumple la demanda en el cuadrante *q*, 0 e.o.c. 
    z = m.addVars(Q, H, vtype=GRB.BINARY, name="z")  # 1 si al momento de haber un crimen a la hora *h* en el cuadrante *q*, existe una patrulla en el mismo cuadrante a la misma hora, 0 e.o.c.
    w = m.addVars(((c, t, q, h) for c in C for t in O[c] for q in J[c] for h in H), vtype=GRB.BINARY, name="w")  # 1 si la patrulla *t¨* de la comisaría *c* está en el cuadrante *q* a la hora *h*, 0 e.o.c.
    s = m.addVars(((c, t, h) for c in C for t in O[c] for h in H), vtype=GRB.BINARY, name="s") # 1 si la patrulla *t* de la comisaría *c* sale a la hora *h*, 0 e.o.c.


    # Definimos las restricciones

    # R1: Stock máximo de patrullas por comisaría
    R1 = m.addConstrs(
        (quicksum(s[c, t, h] for t in O[c] for h in H) <= data['upsilon_c'][c-1] for c in C),
        name="R1"
    )

    # R2: Límite de horas de patrullas por comisaría
    R2 = m.addConstrs(
        (quicksum(w[c, t, q, h] for q in J[c] for h in H) <= data['Pi_c'][t-1] for c in C for t in O[c]),
        name="R2"
    )

    # R3: Restricción de presupuesto    
    R3 = m.addConstrs(
        (quicksum(quicksum(data['K'] * s[c, t, h] + quicksum(w[c, t, q, h] * data['k'] 
        for q in J[c]) for h in H) for t in O[c]) <= data['rho_c'][c-1] for c in C for h in H
        ),
        name="R3"
    )

    # R4: Una patrulla solo puede estar en un cuadrante a la vez
    R4 = m.addConstrs(
        (quicksum(w[c, t, q, h] for q in J[c]) <= 1 for c in C for t in O[c] for h in H),
        name="R5"
    )

    # R5: Se visitan todos los cuadrantes al menos una hora al día
    R5 = m.addConstrs(
    (quicksum(w.get((c, t, q, h), 0) for t in O[c] for h in H) >= 1
        for c in C for q in J[c]),
    name="R5"
    )

    # R6: Una patrulla solo puede salir una vez al día
    R6 = m.addConstrs(
        (quicksum(s[c, t, h] for h in H) <= 1 for c in C for t in O[c]), 
        name="R6"
    )

    # R7 No se puede patrullar si no se sale de la comisaría
    R7 = m.addConstrs(
        (quicksum(w[c, t, q, h] for q in J[c] for h in H) <= quicksum(s[c, t, h] for h in H) * Big_M  for c in C for t in O[c] for h in H),
        name="R7"
    )

    # R8: Activación de Y si y solo si se cumple la demanda
    R8 = m.addConstrs(
        (quicksum(w[c, t, q, h] for t in O[c]) >= y[q, h] * delta[q][h-1] for c in C for q in J[c] for h in H),
        name="R8"
    )

    # R9: Activación de Z si y solo si al momento de haber un crimen a la hora *h* en el cuadrante *q*, existe una patrulla en el mismo cuadrante a la misma hora
    R9 = m.addConstrs(
        (z[q, h] <= w[c, t, q, h] * data['theta_{q,h}'][q-1][h-1] for c in C for t in O[c] for q in J[c] for h in H),
        name="R9"
    )

    # R10: Movimiento entre cuadrantes vecinos
    for c in C:
        for t in O[c]:
            for q in J[c]:
                for h in H[:-1]: 
                    no_vecinos = [q_p for q_p in J[c] if q_p not in V[q] and q_p != q] 
                    if no_vecinos:
                        m.addConstr(
                            w[c, t, q, h] + quicksum(w[c, t, q_p, h+1] for q_p in no_vecinos) <= 1,
                            name="R10")

    # R11: Una patrulla no puede estar más de *1* hora en un cuadrante
    R11 = m.addConstrs(
        (w[c, t, q, h] + w[c, t, q, h+1] <= 1 for c in C for t in O[c] for q in J[c] for h in H[:-1]), 
        name="R11"
    )

    '''
    # R11*: Una patrulla no puede estar más de *MAX_HORAS_SEGUIDAS* horas seguidas en un cuadrante
    MAX_HORAS_SEGUIDAS = 2  ### Definir en parámetros??
    for c in C:
        for t in O[c]:
            for q in J[c]:
                for h in range(1, 23 - MAX_HORAS_SEGUIDAS + 2):  # Asegura que no nos pasemos del rango
                    m.addConstr(
                        quicksum(w[c, t, q, h + offset] for offset in range(MAX_HORAS_SEGUIDAS + 1)) <= MAX_HORAS_SEGUIDAS,
                        name=R11)
    '''

    # R12: Restricción de salida de patrullas
    for c in C:
        for t in O[c]:
            for h in H:
                if h == 0:
                    m.addConstr(
                        s[c, t, h] >= quicksum(w[c, t, q, h] for q in J[c]),
                        name=f"R_salida_inicio_c{c}_t{t}_h{h}"
                    )
                else:
                    m.addConstr(
                        s[c, t, h] >= quicksum(w[c, t, q, h] for q in J[c]) - quicksum(w[c, t, q, h - 1] for q in J[c]),
                        name=f"R_salida_cambio_c{c}_t{t}_h{h}"
                    )


    # Definimos la función objetivo
    m.setObjective(
        quicksum(data['a1'] * y[q, h] + data['a2'] * z[q, h] for h in H for q in Q),
        GRB.MAXIMIZE
    )

    # Analisis de sensibilidad
    def resolver_sensibilidad(cambio):
        
        m.optimize()
        if m.status == GRB.OPTIMAL:
            print(cambio)
            print('-' * 80)
            print(f"\nSolución óptima encontrada en {round(m.runtime, 2)}s: {int(m.ObjVal)} unidades de felicidad\n")
            print('-' * 80)

        return None

    resolver_sensibilidad(f"Analisis al variar {(porcentaje-1)*100}% el presupuesto")