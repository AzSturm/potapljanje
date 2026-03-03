import random

# Ustvari prazno igralno polje
def create_grid(size=10):
    return [[0 for _ in range(size)] for _ in range(size)]

# Preveri, ali je ladjico možno postaviti na mrežo
def can_place_ship(grid, row, col, length, direction):
    if direction == "H":
        if col + length > len(grid[0]):
            return False
        return all(grid[row][col + i] == 0 for i in range(length))
    elif direction == "V":
        if row + length > len(grid):
            return False
        return all(grid[row + i][col] == 0 for i in range(length))

# Postavi ladjico na mrežo
def place_ship(grid, length):
    while True:
        row = random.randint(0, 9)
        col = random.randint(0, 9)
        direction = random.choice(["H", "V"])
        if can_place_ship(grid, row, col, length, direction):
            if direction == "H":
                for i in range(length):
                    grid[row][col + i] = 1
            elif direction == "V":
                for i in range(length):
                    grid[row + i][col] = 1
            break

# Pripravi igralno polje z ladjicami
def setup_player_grid():
    grid = create_grid()
    ships = [5, 4, 3, 3, 2]  # Dolžine ladjic
    for ship in ships:
        place_ship(grid, ship)
    return grid

# Prikaži mrežo z oznakami vrstic in stolpcev
def display_grid(grid, hide_ships=False):
    print("  " + " ".join(str(i) for i in range(1, 11)))  # Oznake stolpcev
    print(" " + "-" * 21)  # Ločnica
    for idx, row in enumerate(grid):
        row_label = chr(65 + idx)  # Pretvori indeks v črko (A-J)
        print(row_label + "|" + " ".join(str(cell) if not hide_ships or cell <= 0 else "x" for cell in row))

# Glavni program
def main():
    print("Dobrodošli v igri Potapljanje ladjic!")
    
    # Ustvari mreži za igralca in računalnik
    player_primary_grid = setup_player_grid()
    computer_primary_grid = setup_player_grid()
    player_target_grid = create_grid()
    computer_target_grid = create_grid()

    print("\nVaša mreža:")
    display_grid(player_primary_grid)

    print("\nRačunalnikova mreža (skrita):")
    display_grid(computer_primary_grid, hide_ships=True)

# Preveri, ali je strel veljaven in posodobi mrežo
def take_shot(target_grid, primary_grid, row, col):
    if target_grid[row][col] != 0:
        print("To polje je že zadeto. Poskusi znova.")
        return False
    if primary_grid[row][col] == 1:
        print("Zadet!")
        target_grid[row][col] = 1  # Označi zadetek
        primary_grid[row][col] = -1  # Označi potopljeno ladjico
    else:
        print("Zgrešil!")
        target_grid[row][col] = -1  # Označi zgrešek
    return True

# Preveri, ali so vse ladjice potopljene
def all_ships_sunk(grid):
    return all(cell != 1 for row in grid for cell in row)

# Glavni program
def main():
    print("Dobrodošli v igri Potapljanje ladjic!")
    
    # Ustvari mreži za igralca in računalnik
    player_primary_grid = setup_player_grid()
    computer_primary_grid = setup_player_grid()
    player_target_grid = create_grid()
    computer_target_grid = create_grid()

    print("\nVaša mreža:")
    display_grid(player_primary_grid)

    while True:
        # Igralec strelja
        print("\nVaša ciljna mreža:")
        display_grid(player_target_grid)
        while True:
            try:
                row = int(input("Vnesi vrstico (0-9): "))
                col = int(input("Vnesi stolpec (0-9): "))
                if 0 <= row < 10 and 0 <= col < 10:
                    if take_shot(player_target_grid, computer_primary_grid, row, col):
                        break
                else:
                    print("Vnesi veljavne koordinate (0-9).")
            except ValueError:
                print("Vnesi številske vrednosti za vrstico in stolpec.")
        
        if all_ships_sunk(computer_primary_grid):
            print("Čestitke! Potopil si vse računalnikove ladjice!")
            break

        # Računalnik strelja
        print("\nRačunalnik strelja...")
        while True:
            row = random.randint(0, 9)
            col = random.randint(0, 9)
            if take_shot(computer_target_grid, player_primary_grid, row, col):
                break
        
        print("\nRačunalnikova ciljna mreža:")
        display_grid(computer_target_grid)

        if all_ships_sunk(player_primary_grid):
            print("Računalnik je potopil vse tvoje ladjice. Izgubil si!")
            break


if __name__ == "__main__":
    main()