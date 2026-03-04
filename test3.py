import tkinter as tk
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
def place_ship(grid, row, col, length, direction):
    if direction == "H":
        for i in range(length):
            grid[row][col + i] = 1
    elif direction == "V":
        for i in range(length):
            grid[row + i][col] = 1

# Preveri, ali so vse ladjice potopljene
def all_ships_sunk(grid):
    return all(cell != 1 for row in grid for cell in row)

# Glavni razred za grafični vmesnik
class BattleshipGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Potapljanje ladjic")
        
        # Ustvari mreži za igralca in računalnik
        self.player_primary_grid = create_grid()
        self.computer_primary_grid = create_grid()
        self.player_target_grid = create_grid()
        self.computer_target_grid = create_grid()

        # Ladjice za postavitev
        self.ships = [5, 4, 3, 3, 2]
        self.current_ship_index = 0

        # Izbrana smer (privzeto vodoravno)
        self.ship_direction = tk.StringVar(value="H")

        # Ustvari gumbe za igralčevo mrežo
        self.player_buttons = [[None for _ in range(10)] for _ in range(10)]
        tk.Label(root, text="Vaša mreža").grid(row=0, column=0, columnspan=10)
        for row in range(10):
            for col in range(10):
                btn = tk.Button(root, width=2, height=1, bg="blue", command=lambda r=row, c=col: self.place_player_ship(r, c))
                btn.grid(row=row + 1, column=col)
                self.player_buttons[row][col] = btn

        # Ustvari gumbe za računalnikovo mrežo
        self.computer_buttons = [[None for _ in range(10)] for _ in range(10)]
        tk.Label(root, text="Računalnikova mreža").grid(row=0, column=11, columnspan=10)
        for row in range(10):
            for col in range(10):
                btn = tk.Button(root, width=2, height=1, bg="blue", state="disabled")
                btn.grid(row=row + 1, column=col + 11)
                self.computer_buttons[row][col] = btn

        # Izbirnik smeri
        tk.Label(root, text="Izberi smer ladjice:").grid(row=12, column=0, columnspan=5)
        tk.Radiobutton(root, text="Vodoravno", variable=self.ship_direction, value="H").grid(row=13, column=0, columnspan=5)
        tk.Radiobutton(root, text="Navpično", variable=self.ship_direction, value="V").grid(row=14, column=0, columnspan=5)

        # Navodila za postavitev ladjic
        self.instructions = tk.Label(root, text=f"Postavi ladjico dolžine {self.ships[self.current_ship_index]}")
        self.instructions.grid(row=15, column=0, columnspan=10)

        # Gumb za začetek igre
        self.start_button = tk.Button(root, text="Začni igro", state="disabled", command=self.start_game)
        self.start_button.grid(row=16, column=0, columnspan=10)

    # Postavi ladjico igralca
    def place_player_ship(self, row, col):
        if self.current_ship_index >= len(self.ships):
            return

        ship_length = self.ships[self.current_ship_index]
        direction = self.ship_direction.get()  # Pridobi izbrano smer

        if can_place_ship(self.player_primary_grid, row, col, ship_length, direction):
            place_ship(self.player_primary_grid, row, col, ship_length, direction)
            for i in range(ship_length):
                if direction == "H":
                    self.player_buttons[row][col + i].config(bg="green", state="disabled")
                elif direction == "V":
                    self.player_buttons[row + i][col].config(bg="green", state="disabled")

            self.current_ship_index += 1
            if self.current_ship_index < len(self.ships):
                self.instructions.config(text=f"Postavi ladjico dolžine {self.ships[self.current_ship_index]}")
            else:
                self.instructions.config(text="Vse ladjice so postavljene!")
                self.start_button.config(state="normal")
        else:
            self.instructions.config(text="Ladjice ni mogoče postaviti tukaj. Poskusi znova.")

    # Začni igro
    def start_game(self):
        self.instructions.config(text="Igra se je začela! Klikni na računalnikovo mrežo za streljanje.")
        for row in range(10):
            for col in range(10):
                self.computer_buttons[row][col].config(state="normal", command=lambda r=row, c=col: self.player_shoot(r, c))

        # Računalnik postavi svoje ladjice
        for ship_length in self.ships:
            while True:
                row = random.randint(0, 9)
                col = random.randint(0, 9)
                direction = random.choice(["H", "V"])
                if can_place_ship(self.computer_primary_grid, row, col, ship_length, direction):
                    place_ship(self.computer_primary_grid, row, col, ship_length, direction)
                    break

    # Igralec strelja
    def player_shoot(self, row, col):
        if self.player_target_grid[row][col] != 0:
            return  # Polje je že zadeto
        if self.computer_primary_grid[row][col] == 1:
            self.computer_buttons[row][col].config(bg="red")  # Zadet ladjico
            self.player_target_grid[row][col] = 1
            self.computer_primary_grid[row][col] = -1
        else:
            self.computer_buttons[row][col].config(bg="white")  # Zgrešil
            self.player_target_grid[row][col] = -1

        if all_ships_sunk(self.computer_primary_grid):
            self.instructions.config(text="Čestitke! Zmagal si!")
            self.disable_all_buttons()
            return

        self.computer_shoot()

    # Računalnik strelja
    def computer_shoot(self):
        self.instructions.config(text="Računalnik strelja...")
        while True:
            row = random.randint(0, 9)
            col = random.randint(0, 9)
            if self.computer_target_grid[row][col] == 0:
                if self.player_primary_grid[row][col] == 1:
                    self.player_buttons[row][col].config(bg="red")  # Zadet ladjico
                    self.computer_target_grid[row][col] = 1
                    self.player_primary_grid[row][col] = -1
                else:
                    self.player_buttons[row][col].config(bg="white")  # Zgrešil
                    self.computer_target_grid[row][col] = -1
                break

        if all_ships_sunk(self.player_primary_grid):
            self.instructions.config(text="Računalnik je zmagal!")
            self.disable_all_buttons()
            return

        self.instructions.config(text="Tvoj na vrsti! Klikni na računalnikovo mrežo.")

    # Onemogoči vse gumbe (po koncu igre)
    def disable_all_buttons(self):
        for row in range(10):
            for col in range(10):
                self.computer_buttons[row][col].config(state="disabled")
                self.player_buttons[row][col].config(state="disabled")

# Zaženi igro
if __name__ == "__main__":
    root = tk.Tk()
    game = BattleshipGame(root)
    root.mainloop()