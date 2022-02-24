from statistics import mean
import os

# deletes the symbol in the end (as we go to the next line)
with open('Results.txt', 'rb+') as filehandle:
    filehandle.seek(-1, os.SEEK_END)
    filehandle.truncate()
# reads the data
with open('Results.txt', 'r') as fin:
    data = [float(x) for x in fin.read().split('\n')]
# calculates the mean value
average = mean(data)
print(average)

