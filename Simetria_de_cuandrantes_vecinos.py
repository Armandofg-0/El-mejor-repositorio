import pandas as pd
import os


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
            print(x, y)
            print(df.iloc[x,y], df.iloc[y, x])

print("fin")
