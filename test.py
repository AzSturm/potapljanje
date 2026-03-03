vrstice = 10
stolpci = 10
stevilke = [chr(ord('A') + i) for i in range(vrstice)]
crke = list(range(1, stolpci + 1))

polje = []

for r in range(vrstice):
    vrsta = []
    for c in range(stolpci):
        vrsta.append("x")
    polje.append(vrsta)

print(polje)
