import pandas as pd
import os

'''
def os_join(path):
    return os.path.join("data", path)


df = pd.read_csv(os_join("cuadrantes_vecinos.csv"), header=None)
df = df.drop(df.columns[0], axis=1)

len_x, len_y = df.shape

print(df)

def seguro(x):
    try:
        a = int(x)
        return a
    except:
        return "string"


for x in range(len_x):
    for y in range(len_y):
        if (isinstance(seguro(df.iloc[x, y]), int)  and not isinstance(seguro(df.iloc[y, x]), int)) or (
            not isinstance(seguro(df.iloc[x, y]), int) and isinstance(seguro(df.iloc[y, x]), int)
        ):
            print("pos:")
            print(x+1, y+1)
            print("val:")
            print(df.iloc[x,y], df.iloc[y, x])

print("fin")
'''

### demanda por cuadrante
import random
numeros = []
for i in range(1, 81):
    fila = []
    for i in range(1, 25):
        hora = random.randint(1, 3) # Randint por cuadrante y por hora
        fila.append(hora)
    numeros.append(fila)

cont = 1
for linea in numeros:
    txt = ''
    for item in linea:
        txt = txt + str(item) + ','
    cont += 1
    txt = txt[0:47]
    print(txt)
print(cont)
