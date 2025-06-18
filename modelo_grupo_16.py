import pandas as pd
import os
from gurobipy import Model, GRB, quicksum

def os_join(path):
    return os.path.join("data", path)

# Definimos los parámetros
data = {}
data['upsilon_c'] = pd.read_csv(os_join('comisarias.csv'), usecols=['total_patrullas_por_comisaria']).squeeze()
data['upsilon_c'].index = data['upsilon_c'].index + 1
data['upsilon_c'] = data['upsilon_c'].values

data['pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_min']).squeeze().values

data['Pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_max']).squeeze()
data['Pi_c'].index = data['Pi_c'].index + 1
data['Pi_c'] = data['Pi_c'].values

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
data['r'] = pd.read_csv(os_join('cuadrantes.csv')).squeeze().values
data['B'] = pd.read_csv(os_join('comisarias.csv')).squeeze().values           
data['f'] = pd.read_csv(os_join('patrullas.csv')).squeeze().values

# Creamos conjuntos
Q = range(1, len(data["r"]) + 1) # Conjunto de cuadrantes
C = range(1, len(data["B"]) + 1) # Conjunto de comisarías
T = range(1 ,len(data['f']) + 1) # Conjunto de patrullas
H = range(1, 25) # Conjunto de horas
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
p = m.addVars(C, T, vtype=GRB.BINARY, name="p")  # 1 si la patrulla *t* sale de la comisaría *c*, 0 e.o.c.
w = m.addVars(((c, t, q, h) for c in C for t in O[c] for q in J[c] for h in H), vtype=GRB.BINARY, name="w")  # 1 si la patrulla *t¨* de la comisaría *c* está en el cuadrante *q* a la hora *h*, 0 e.o.c.


# Definimos las restricciones

# R1: Stock máximo de patrullas por comisaría
R1 = m.addConstrs(
    (quicksum(p[c, t] for t in O[c]) <= data['upsilon_c'][c-1] for c in C),
    name="R1"
)

# R2: Límite de horas de patrullas por comisaría
R2 = m.addConstrs(
    (quicksum(w[c, t, q, h] for q in J[c] for h in H) <= data['Pi_c'][t-1] for c in C for t in O[c]),
    name="R2"
)

# R3: Restricción de presupuesto    
R3 = m.addConstrs(
    (quicksum(data['K'] * p[c, t] + quicksum(w[c, t, q, h] * data['k'] 
    for h in H for q in J[c]) for t in O[c]) <= data['rho_c'][c-1]for c in C
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

# R6 No se puede patrullar si no se sale de la comisaría
R6 = m.addConstrs(
    (quicksum(w[c, t, q, h] for q in J[c]) <= p[c, t] * Big_M for c in C for t in O[c] for h in H),
    name="R6"
)

# R7: Activación de Y si y solo si se cumple la demanda
R7 = m.addConstrs(
    (quicksum(w[c, t, q, h] for t in O[c]) >= y[q, h] * delta[q][h-1] for c in C for q in J[c] for h in H),
    name="R7"
)

# R8: Activación de Z si y solo si al momento de haber un crimen a la hora *h* en el cuadrante *q*, existe una patrulla en el mismo cuadrante a la misma hora
R8 = m.addConstrs(
    (z[q, h] <= w[c, t, q, h] * data['theta_{q,h}'][q-1][h-1] for c in C for t in O[c] for q in J[c] for h in H),
    name="R8"
)

# R9: Movimiento entre cuadrantes vecinos
for c in C:
    for t in O[c]:
        for q in J[c]:
            for h in H[:-1]: 
                no_vecinos = [q_p for q_p in J[c] if q_p not in V[q] and q_p != q] 
                if no_vecinos:
                    m.addConstr(
                        w[c, t, q, h] + quicksum(w[c, t, q_p, h+1] for q_p in no_vecinos) <= 1,
                        name="R9")

# Definimos la función objetivo
m.setObjective(
    quicksum(data['a1'] * y[q, h] + data['a2'] * z[q, h] for h in H for q in Q),
    GRB.MAXIMIZE
)

# Resolvemos el modelo

m.optimize()

# Imprimimos los resultados

if m.status == GRB.OPTIMAL:
    print('-' * 80)
    print(f'\nVariable w_[c, t, q, h]:')
    print(f'Recorrido de cada patrulla a lo largo de las horas del día:\n')
    for c, t, q, h in w.keys(): # w.keys() devuelve todas las tuplas de índices para las que 'w' existe
        if w[c, t, q, h].X == 1: # Si la variable binaria es 1 (o muy cerca de 1)
            print(f" Patrulla {t} de la comisaría {c} está en el cuadrante {q} a la hora {h}")

    print()
    print('-' * 80)
    print(f'\nTotal de horas recorridas de cada patrulla t:\n')
    for c in C:
        for t in O[c]:
            horas_activas = sum(w[c, t, q, h].X
                            for q in J[c] # Suma solo sobre los cuadrantes asociados a la comisaría 'c'
                            for h in H
                            if (c, t, q, h) in w) # Asegurarse de que la variable existe  
            print(f" Patrulla {t} de la comisaría {c}: Horas activas = {horas_activas:.0f}, horas máx: {data['Pi_c'][t-1]}")

    demanda_cumplida = 0
    for q, h in y.keys():
        if y[q, h].X == 1:
            demanda_cumplida += 1

    print()
    print('-' * 80)
    print(f'\nVariable y_[q, h]:\n')
    print(f'Total de casos posibles de cumplimiento de demanda = {80 * 24}')
    print(f'Total de veces que se cumplió la demanda = {demanda_cumplida}\n')
    print('-' * 80)

    patrulla_presente = 0
    patrulla_no_presente = 0
    for q in Q:
        for h in H:
            if data['theta_{q,h}'][q - 1][h-1] == 1:
                if z[q, h].X == 1:
                    patrulla_presente += 1
                else:
                    patrulla_no_presente += 1

    print(f'\nVariable z_[q, h]:')
    print(f'\nTotal de crimenes = {patrulla_presente + patrulla_no_presente}')    
    print(f'Total de crímenes en los que hubo alguna patrulla en el mismo cuadrante = {patrulla_presente}\n')

    print('-' * 80)
    print(f"\nSolución óptima encontrada en {round(m.runtime, 2)}s: {int(m.ObjVal)} unidades de felicidad\n")
    print('-' * 80)
