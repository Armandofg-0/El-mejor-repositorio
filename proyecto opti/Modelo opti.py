import pandas as pd
from gurobipy import Model, GRB, quicksum

# Definimos los parámetros
data = {}
data["delta_q"] = pd.read_csv('demanda_cuadrante_hora.csv', header=None).squeeze().values # Matriz que contiene: la demanda de cada cuadrante por horas (posible cambio a días)
data['pi_c'] = pd.read_csv('patrullas.csv', usecols=['horas_min']).squeeze().values
data['Pi_c'] = pd.read_csv('patrullas.csv', usecols=['horas_max']).squeeze().values
data['K'] = pd.read_csv('costos.csv', usecols=['costo_fijo']).squeeze()
data['k'] = pd.read_csv('costos.csv', usecols=['costo_por_hora']).squeeze()
data['a1'] = pd.read_csv('ponderadores_fo.csv', usecols=['a1']).squeeze()
data['a2'] = pd.read_csv('ponderadores_fo.csv', usecols=['a2']).squeeze()



c_vecinos = pd.read_csv('cuadrantes_vecinos.csv', header=None)
comisarias = pd.read_csv('cuadrantes.csv')
data['r'] = pd.read_csv('cuadrantes.csv').squeeze().values
data['B'] = pd.read_csv('Total de comisarias.csv').squeeze().values
data['f'] = pd.read_csv('patrullas.csv').squeeze().values

# Creamos conjuntos
Q = range(len(data["r"])) # Conjunto de cuadrantes
C = range(len(data["B"])) # Conjunto de comisarías
T = range(len(data["f"])) # Conjunto de patrullas
H = range(1,24) # Conjunto de horas
J = comisarias.groupby('id_comisaría_asociada')['id_cuadrante'].apply(list).to_dict()
V = {}

for i, fila in c_vecinos.iterrows():
    vecinos = []
    for j, num in enumerate(fila):
        if num != '-':
            vecinos.append(int(num))  # o int(val) si el número que aparece es el id del vecino
    V[i] = vecinos

print(V)



data['f'] = pd.read_csv('patrullas.csv').squeeze().values
data['n'] = pd.read_csv('cuadrantes_vecinos.csv').squeeze().values
data['F'] = pd.read_csv('cuadrantes_vecinos.csv', header=None).squeeze().values
data['g'] = pd.read_csv('costos.csv').squeeze().values
