import pandas as pd

df = pandas.DataFrame(columns= ['id','name', 'age', 'grade'])

new_row = {'id': 'name', 1: 'John', 'age': 28, 'grade': 'B+'}

df = pd.concat([df, pd.DataFrame(new_row)], ignore_index=True)

print(df)