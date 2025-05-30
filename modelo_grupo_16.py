import pandas as pd
import os
from gurobipy import Model, GRB, quicksum

def os_join(path):
    return os.path.join("data", path)

# Definimos los parámetros
data = {}
data["delta_q"] = pd.read_csv(os_join('cuadrantes.csv'), usecols=['demanda_por_dia']).squeeze().values # Matriz que contiene: la demanda de cada cuadrante por horas (posible cambio a días)
data['upsilon_c'] = pd.read_csv(os_join('comisarias.csv'), usecols=['total_patrullas_por_comisaria']).squeeze().values
data['pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_min']).squeeze().values
data['Pi_c'] = pd.read_csv(os_join('patrullas.csv'), usecols=['horas_max']).squeeze().values
data['K'] = pd.read_csv(os_join('costos.csv'), usecols=['costo_fijo']).squeeze()
data['k'] = pd.read_csv(os_join('costos.csv'), usecols=['costo_por_hora']).squeeze()
data['rho_c'] = pd.read_csv(os_join('comisarias.csv'), usecols=['presupuesto_diario_comisaria']).squeeze().values
data['theta_{q,h}'] = pd.read_csv(os_join('crimenes_por_hora.csv'), header=None)
data['a1'] = pd.read_csv(os_join('ponderadores_fo.csv'), usecols=['a1']).squeeze()
data['a2'] = pd.read_csv(os_join('ponderadores_fo.csv'), usecols=['a2']).squeeze()
Big_M = 1000000  


c_vecinos = pd.read_csv(os_join('cuadrantes_vecinos.csv'), header=None)
comisarias = pd.read_csv(os_join('cuadrantes.csv'))
data['r'] = pd.read_csv(os_join('cuadrantes.csv')).squeeze().values
data['B'] = pd.read_csv(os_join('comisarias.csv')).squeeze().values           
data['f'] = pd.read_csv(os_join('patrullas.csv')).squeeze().values

# Creamos conjuntos
Q = range(1, len(data["r"])) # Conjunto de cuadrantes
C = range(1, len(data["B"])) # Conjunto de comisarías
T = range(1 ,len(data["f"])) # Conjunto de patrullas
H = range(1,24) # Conjunto de horas
J = comisarias.groupby('id_comisaría_asociada')['id_cuadrante'].apply(list).to_dict()
V = {}

for i, fila in c_vecinos.iterrows():
    vecinos = []
    for j, num in enumerate(fila):
        if num != '-':
            vecinos.append(int(num))  # o int(val) si el número que aparece es el id del vecino
    V[i+1] = vecinos

data['f'] = pd.read_csv(os_join('patrullas.csv')).squeeze().values
data['n'] = pd.read_csv(os_join('cuadrantes_vecinos.csv')).squeeze().values
data['F'] = pd.read_csv(os_join('cuadrantes_vecinos.csv'), header=None).squeeze().values
data['g'] = pd.read_csv(os_join('costos.csv')).squeeze().values


# Definimos el modelo
m = Model("Modelo de Optimización de Patrullas")


# Definimos las variables de decisión       
y = m.addVars(Q, vtype=GRB.BINARY, name="y")  # 1 si se cumple la demanda en el cuadrante *q*, 0 e.o.c. 
z = m.addVars(Q, H, vtype=GRB.BINARY, name="z")  # 1 si al momento de haber un crimen a la hora *h* en el cuadrante *q*, existe una patrulla en el mismo cuadrante a la misma hora, 0 e.o.c.
p = m.addVars(C, T, vtype=GRB.BINARY, name="p")  # 1 si la patrulla *t* sale de la comisaría *c*, 0 e.o.c.
w = m.addVars(C, T, Q, H, vtype=GRB.BINARY, name="w")  # 1 si la patrulla *t¨* de la comisaría *c* está en el cuadrante *q* a la hora *h*, 0 e.o.c.


# Definimos las restricciones

# R1: Una patrulla solo puede visitar los cuadrantes que le corresponden
R1 = m.addConstrs(
    (w[c, t, q, h] == 0
     for c in C for t in T for q in Q for h in H if q not in J[c]),
    name="R1"
)

# R2: Stock máximo de patrullas por comisaría
R2 = m.addConstrs(
    (quicksum(p[c, t] for t in T) <= data['upsilon_c'][c] for c in C),
    name="R2"
)
"""
# R3: Límite de horas de patrullas por comisaría
R3 = m.addConstr(
    (data['pi_c'] <= quicksum(w[c, t, q, h] for q in Q for h in H) <= data['Pi_c'][t] for c in C for t in T),
    name="R3"
)"""

# R4: Restricción de presupuesto    
R4 = m.addConstr(
    ((quicksum(data['K'] * p[c, t] + quicksum(w[c, t, q, h] * data['k'] for h in H for q in Q) for t in T) <= data['rho_c']) for c in C),
    name="R4"
)
'''
# R5: Una patrulla solo puede estar en un cuadrante a la vez
R5 = m.addConstr(
    (quicksum(w[c, t, q, h] for q in Q) <= 1 for c in C for t in T for h in H),
    name="R5"
)

# R6: Una patrulla tiene que estar asignada a una sola comisaria
R6 = m.addConstr(
    (quicksum(w[c, t, q, h] for c in C) == 1 for t in T for h in H for q in Q),
    name="R6"
)

# R7: Se visitan todos los cuadrantes al menos una hora al día
R7 = m.addConstr(
    (quicksum(w[c, t, q, h] for h in H for t in T) >= 1 for c in C for q in Q),
    name="R7"
)

# R8 No se puede patrullar si no se sale de la comisaría
R8 = m.addConstr(
    (quicksum(w[c, t, q, h] for q in Q) <= p[c, t] * Big_M for c in C for t in T for h in H),
    name="R8"
)

# R9: Activación de Y si y solo si se cumple la demanda
R9 = m.addConstr(
    (quicksum(w[c, t, q, h] for h in H for t in T) - data['delta_q'] <= Big_M * y[q] for q in Q for c in C),
    name="R10"
)

# R10: Activación de Z si y solo si al momento de haber un crimen a la hora *h* en el cuadrante *q*, existe una patrulla en el mismo cuadrante a la misma hora
R10 = m.addConstr(
    (w[c, t, q, h] * data['theta_{q,h}'] == z[q, h]  for c in C for t in T for q in Q for h in H),
    name="R11"
)

# R11: Movimiento entre cuadrantes vecinos
R11 = m.addConstr(
    (quicksum(w[c, t, q, h] for q in V[q2]) - quicksum(w[c, t, q2, h] for q2 in V[q]) == 0 for c in C for t in T for q in Q for q2 in Q for h in H),
    name="R13"
)

# Definimos la función objetivo
m.setObjective(
    quicksum(data['a1'] * y[q]  + 
    quicksum(data['a2'] * z[q, h] for h in H) for q in Q),
    GRB.MAXIMIZE
)

# Resolvemos el modelo
m.optimize()

# Imprimimos los resultados
if m.status == GRB.OPTIMAL:
    print("Solución óptima encontrada:")
    for q in Q:
        if y[q].X > 0.5:  # Si se cumple la demanda en el cuadrante q
            print(f"Cuadrante {q}: Demanda cumplida")
    for c in C:
        for t in T:
            if p[c, t].X > 0.5:  # Si la patrulla t sale de la comisaría c
                print(f"Comisaría {c}, Patrulla {t}: Sale de la comisaría")
    for q in Q:
        for h in H:
            if z[q, h].X > 0.5:  # Si hay una patrulla en el cuadrante q a la hora h
                print(f"Cuadrante {q}, Hora {h}: Patrulla presente")
'''