try:
    import tkinter as tk
except ModuleNotFoundError as exc:
    if getattr(exc, "name", None) == "tkinter":
        raise SystemExit(
            "Manjka modul 'tkinter'. Na Ubuntu/Debian ga namestiš z:\n"
            "  sudo apt update && sudo apt install python3-tk\n"
            "Nato ponovno zaženi program z /usr/bin/python3."
        ) from exc
    raise
import random
from pathlib import Path
from math import ceil

try:
    from PIL import Image  # type: ignore
except ModuleNotFoundError:
    Image = None

try:
    from PIL import ImageTk  # type: ignore
except Exception:
    # Na Debian/Ubuntu je ImageTk pogosto v ločenem paketu python3-pil.imagetk.
    ImageTk = None

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


def placement_block_reason(grid, row, col, length, direction):
    if direction == "H":
        if col + length > len(grid[0]):
            return "izven mreže"
        if any(grid[row][col + i] != 0 for i in range(length)):
            return "prekriva drugo ladjo"
        return None
    if direction == "V":
        if row + length > len(grid):
            return "izven mreže"
        if any(grid[row + i][col] != 0 for i in range(length)):
            return "prekriva drugo ladjo"
        return None
    return "neznana smer"

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

        self.player_ship_placements = []
        self.computer_ship_placements = []

        self.game_started = False
        self.game_over = False
        self.waiting_for_computer_shot = False

        # Velikost celice v piksljih za prikaz segmenta ladje.
        self.cell_px = 20

        # Zunanji rob levo/desno okoli mrež.
        self.outer_pad_x = 14

        self.board_w_px = self.cell_px * 10
        self.separator_w_px = 2
        self.separator_pad_x = 6
        self.ui_total_w_px = (
            self.outer_pad_x
            + self.board_w_px
            + self.separator_pad_x
            + self.separator_w_px
            + self.separator_pad_x
            + self.board_w_px
            + self.outer_pad_x
        )

        # Naloži slike ladij (ena slika čez več celic, tudi navpično).
        self.ship_images = self.load_ship_images()
        self.hit_ship_images = self.load_ship_images(hit_variant=True)
        if not self.hit_ship_images:
            self.hit_ship_images = self.ship_images
        self.fire_image = self.load_fire_image()

        # Stabilen layout: 3 stolpci (igralec | ločnica | računalnik).
        self.board_frame = tk.Frame(root)
        self.board_frame.grid(row=0, column=0, sticky="w")

        # Canvas mreži (namesto gumbov) omogočata risanje ene slike čez več celic.
        tk.Label(self.board_frame, text="Vaša mreža").grid(row=0, column=0, padx=(self.outer_pad_x, 0), sticky="w")
        self.player_canvas = tk.Canvas(
            self.board_frame,
            width=self.board_w_px,
            height=self.board_w_px,
            highlightthickness=0,
        )
        self.player_canvas.grid(row=1, column=0, padx=(self.outer_pad_x, 0), sticky="w")
        self.draw_grid(self.player_canvas, water_color="blue")
        self.player_canvas.bind("<Button-1>", lambda e: self.on_player_canvas_click(e, "V"))
        self.player_canvas.bind("<Button-3>", lambda e: self.on_player_canvas_click(e, "H"))
        self.player_canvas.bind("<Button-2>", lambda e: self.on_player_canvas_click(e, "H"))

        # Vizualna ločnica med mrežama.
        tk.Frame(self.board_frame, bg="black", width=self.separator_w_px).grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="ns",
            padx=self.separator_pad_x,
        )

        tk.Label(self.board_frame, text="Računalnikova mreža").grid(row=0, column=2, padx=(0, self.outer_pad_x), sticky="w")
        self.computer_canvas = tk.Canvas(
            self.board_frame,
            width=self.board_w_px,
            height=self.board_w_px,
            highlightthickness=0,
        )
        self.computer_canvas.grid(row=1, column=2, padx=(0, self.outer_pad_x), sticky="w")
        self.draw_grid(self.computer_canvas, water_color="green")
        self.computer_canvas.bind("<Button-1>", self.on_computer_canvas_click)

        # Spodnji del (navodila + gumb) ima fiksno širino in dovolj višine,
        # da se okno ne spreminja in da je gumb vedno viden.
        self.bottom_frame = tk.Frame(root, width=self.ui_total_w_px, height=90)
        self.bottom_frame.grid(row=1, column=0, sticky="w")
        self.bottom_frame.grid_propagate(False)

        # Navodila za postavitev ladjic
        self.instructions = tk.Label(
            self.bottom_frame,
            text=(
                f"Postavi ladjico dolžine {self.ships[self.current_ship_index]} "
                "(levi klik = navpično, desni klik = vodoravno)"
            ),
            justify="left",
            anchor="w",
            wraplength=self.ui_total_w_px,
        )
        self.instructions.grid(row=0, column=0, sticky="w", padx=(self.outer_pad_x, self.outer_pad_x), pady=(6, 2))

        # Gumb za začetek igre
        self.start_button = tk.Button(self.bottom_frame, text="Začni igro", state="disabled", command=self.start_game)
        self.start_button.grid(row=1, column=0, sticky="w", padx=(self.outer_pad_x, self.outer_pad_x), pady=(0, 6))

        self.player_shot_markers = {}
        self.computer_shot_markers = {}
        self.revealed_computer_ships = set()

    def draw_grid(self, canvas, water_color):
        canvas.delete("all")
        w = self.cell_px * 10
        h = self.cell_px * 10
        canvas.create_rectangle(0, 0, w, h, fill=water_color, outline=water_color)
        for i in range(11):
            x = i * self.cell_px
            y = i * self.cell_px
            canvas.create_line(x, 0, x, h, fill="black")
            canvas.create_line(0, y, w, y, fill="black")

    def event_to_cell(self, event):
        col = int(event.x // self.cell_px)
        row = int(event.y // self.cell_px)
        if 0 <= row < 10 and 0 <= col < 10:
            return row, col
        return None

    def on_player_canvas_click(self, event, direction):
        if self.game_started or self.game_over:
            return "break"

        cell = self.event_to_cell(event)
        if cell is None:
            self.instructions.config(text="Klik izven mreže.")
            return "break"

        row, col = cell
        try:
            # Pomaga pri diagnostiki, če klik/vezava ne deluje.
            self.instructions.config(text=f"Klik: ({row}, {col}), smer={direction}")
            self.place_player_ship(row, col, direction)
        except Exception as exc:
            self.instructions.config(text=f"Napaka pri kliku: {type(exc).__name__}: {exc}")

        return "break"

    def on_computer_canvas_click(self, event):
        if (not self.game_started) or self.game_over or self.waiting_for_computer_shot:
            return "break"
        cell = self.event_to_cell(event)
        if cell is None:
            return "break"
        row, col = cell
        self.player_shoot(row, col)
        return "break"

    def load_ship_images(self, hit_variant=False):
        images = {}
        base_dir = Path(__file__).parent

        for length in sorted(set(self.ships)):
            suffix = "_zadeta" if hit_variant else ""
            filename = f"ladja{length}x1{suffix}.png"
            path = base_dir / filename
            if not hit_variant and not path.exists() and length == 5:
                fallback = base_dir / "ship.png"
                if fallback.exists():
                    path = fallback

            if not path.exists():
                continue

            target_h = self.cell_px
            target_w = self.cell_px * length

            if Image is not None and ImageTk is not None:
                try:
                    base_img = Image.open(path).convert("RGBA")
                except Exception:
                    continue

                horiz = base_img.resize((target_w, target_h), resample=Image.NEAREST)
                vert = horiz.rotate(90, expand=True)

                images[(length, "H")] = ImageTk.PhotoImage(horiz)
                images[(length, "V")] = ImageTk.PhotoImage(vert)
                continue

            # Fallback brez Pillow: podprto samo, če obstaja eksplicitna navpična slika.
            try:
                horiz = tk.PhotoImage(file=str(path))
            except tk.TclError:
                continue

            if horiz.width() < target_w or horiz.height() < target_h:
                zoom_x = max(1, ceil(target_w / horiz.width()))
                zoom_y = max(1, ceil(target_h / horiz.height()))
                horiz = horiz.zoom(zoom_x, zoom_y)
            if horiz.width() > target_w or horiz.height() > target_h:
                subsample_x = max(1, ceil(horiz.width() / target_w))
                subsample_y = max(1, ceil(horiz.height() / target_h))
                horiz = horiz.subsample(subsample_x, subsample_y)

            images[(length, "H")] = horiz

            v_path = base_dir / f"ladja{length}x1_v.png"
            if v_path.exists():
                try:
                    vert = tk.PhotoImage(file=str(v_path))
                except tk.TclError:
                    continue

                target_v_w = self.cell_px
                target_v_h = self.cell_px * length
                if vert.width() < target_v_w or vert.height() < target_v_h:
                    zoom_x = max(1, ceil(target_v_w / vert.width()))
                    zoom_y = max(1, ceil(target_v_h / vert.height()))
                    vert = vert.zoom(zoom_x, zoom_y)
                if vert.width() > target_v_w or vert.height() > target_v_h:
                    subsample_x = max(1, ceil(vert.width() / target_v_w))
                    subsample_y = max(1, ceil(vert.height() / target_v_h))
                    vert = vert.subsample(subsample_x, subsample_y)

                images[(length, "V")] = vert

        if any(k[1] == "V" for k in images.keys()):
            return images

        if images and (Image is None or ImageTk is None):
            raise SystemExit(
                "Za navpične PNG ladje je potrebna podpora PIL.ImageTk (Tk integracija).\n"
                "Namesti eno od možnosti:\n"
                "  pip install pillow\n"
                "ali na Ubuntu/Debian:\n"
                "  sudo apt update && sudo apt install python3-pil python3-pil.imagetk\n"
                "Alternativa brez Pillow: dodaj datoteke 'ladjaNx1_v.png' za navpične ladje."
            )

        return images

    def load_fire_image(self):
        base_dir = Path(__file__).parent
        fire_path = base_dir / "ogenj.png"
        if not fire_path.exists():
            return None

        target_size = self.cell_px

        if Image is not None and ImageTk is not None:
            try:
                fire = Image.open(fire_path).convert("RGBA")
                fire = fire.resize((target_size, target_size), resample=Image.NEAREST)
                return ImageTk.PhotoImage(fire)
            except Exception:
                return None

        try:
            fire = tk.PhotoImage(file=str(fire_path))
        except tk.TclError:
            return None

        if fire.width() < target_size or fire.height() < target_size:
            zoom_x = max(1, ceil(target_size / fire.width()))
            zoom_y = max(1, ceil(target_size / fire.height()))
            fire = fire.zoom(zoom_x, zoom_y)
        if fire.width() > target_size or fire.height() > target_size:
            subsample_x = max(1, ceil(fire.width() / target_size))
            subsample_y = max(1, ceil(fire.height() / target_size))
            fire = fire.subsample(subsample_x, subsample_y)

        return fire

    def draw_ship(self, canvas, row, col, ship_length, direction, tag):
        img = self.ship_images.get((ship_length, direction))
        if tag.startswith("player_ship_sunk_") or tag.startswith("computer_ship_sunk_"):
            img = self.hit_ship_images.get((ship_length, direction), img)
        x = col * self.cell_px
        y = row * self.cell_px
        if img is not None:
            canvas.create_image(x, y, image=img, anchor="nw", tags=(tag, "ship"))
            canvas.tag_raise("ship")
            canvas.tag_raise("shot")
            canvas.tag_lower("shot_under", "ship")
            return

        # Fallback: če ni slike, nariši enostaven pravokotnik.
        if direction == "H":
            canvas.create_rectangle(
                x,
                y,
                x + ship_length * self.cell_px,
                y + self.cell_px,
                fill="darkgreen",
                outline="black",
                tags=(tag, "ship"),
            )
        else:
            canvas.create_rectangle(
                x,
                y,
                x + self.cell_px,
                y + ship_length * self.cell_px,
                fill="darkgreen",
                outline="black",
                tags=(tag, "ship"),
            )

        canvas.tag_raise("ship")
        canvas.tag_raise("shot")
        canvas.tag_lower("shot_under", "ship")

    def draw_shot_marker(self, canvas, marker_dict, row, col, hit):
        key = (row, col)
        if key in marker_dict:
            return

        pad = 2
        x1 = col * self.cell_px + pad
        y1 = row * self.cell_px + pad
        x2 = (col + 1) * self.cell_px - pad
        y2 = (row + 1) * self.cell_px - pad
        if hit and self.fire_image is not None:
            image_x = col * self.cell_px
            image_y = row * self.cell_px
            under_id = canvas.create_image(image_x, image_y, image=self.fire_image, anchor="nw", tags=("shot_under",))
            top_id = canvas.create_image(image_x, image_y, image=self.fire_image, anchor="nw", tags=("shot",))
            marker_dict[key] = (under_id, top_id)
            canvas.tag_raise("shot")
            if canvas.find_withtag("ship"):
                canvas.tag_lower("shot_under", "ship")
            else:
                canvas.tag_lower("shot_under")
            return

        color = "red" if hit else "white"
        marker_dict[key] = canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", tags=("shot",))

    def get_ship_cells(self, row, col, ship_length, direction):
        if direction == "H":
            return [(row, col + i) for i in range(ship_length)]
        return [(row + i, col) for i in range(ship_length)]

    def get_ship_placement_by_cell(self, placements, row, col):
        for idx, (ship_row, ship_col, ship_length, direction) in enumerate(placements):
            if (row, col) in self.get_ship_cells(ship_row, ship_col, ship_length, direction):
                return idx, ship_row, ship_col, ship_length, direction
        return None

    def mark_player_ship_sunk(self, row, col):
        ship_info = self.get_ship_placement_by_cell(self.player_ship_placements, row, col)
        if ship_info is None:
            return None

        idx, ship_row, ship_col, ship_length, direction = ship_info
        ship_cells = self.get_ship_cells(ship_row, ship_col, ship_length, direction)
        if not all(self.player_primary_grid[r][c] == -1 for r, c in ship_cells):
            return None

        original_tag = f"player_ship_{idx}"
        sunk_tag = f"player_ship_sunk_{idx}"
        self.player_canvas.delete(original_tag)
        self.player_canvas.delete(sunk_tag)
        self.draw_ship(self.player_canvas, ship_row, ship_col, ship_length, direction, tag=sunk_tag)
        return ship_length

    def mark_computer_ship_sunk(self, row, col):
        ship_info = self.get_ship_placement_by_cell(self.computer_ship_placements, row, col)
        if ship_info is None:
            return None

        idx, ship_row, ship_col, ship_length, direction = ship_info
        if idx in self.revealed_computer_ships:
            return None

        ship_cells = self.get_ship_cells(ship_row, ship_col, ship_length, direction)
        if not all(self.computer_primary_grid[r][c] == -1 for r, c in ship_cells):
            return None

        for r, c in ship_cells:
            marker = self.computer_shot_markers.pop((r, c), None)
            if isinstance(marker, tuple) and len(marker) == 2:
                under_id, top_id = marker
                self.computer_canvas.delete(under_id)
                self.computer_canvas.delete(top_id)
            elif isinstance(marker, int):
                self.computer_canvas.delete(marker)

        sunk_tag = f"computer_ship_sunk_{idx}"
        self.computer_canvas.delete(sunk_tag)
        base_img = self.ship_images.get((ship_length, direction))
        hit_img = self.hit_ship_images.get((ship_length, direction))
        x = ship_col * self.cell_px
        y = ship_row * self.cell_px
        if base_img is not None:
            self.computer_canvas.create_image(x, y, image=base_img, anchor="nw", tags=(sunk_tag,))
        if hit_img is not None:
            self.computer_canvas.create_image(x, y, image=hit_img, anchor="nw", tags=(sunk_tag,))
        if base_img is None and hit_img is None:
            if direction == "H":
                self.computer_canvas.create_rectangle(
                    x,
                    y,
                    x + ship_length * self.cell_px,
                    y + self.cell_px,
                    fill="darkgreen",
                    outline="black",
                    width=2,
                    tags=(sunk_tag,),
                )
            else:
                self.computer_canvas.create_rectangle(
                    x,
                    y,
                    x + self.cell_px,
                    y + ship_length * self.cell_px,
                    fill="darkgreen",
                    outline="black",
                    width=2,
                    tags=(sunk_tag,),
                )

        self.computer_canvas.tag_raise(sunk_tag)
        self.revealed_computer_ships.add(idx)
        return ship_length

    # Postavi ladjico igralca
    def place_player_ship(self, row, col, direction):
        if self.current_ship_index >= len(self.ships):
            return

        ship_length = self.ships[self.current_ship_index]

        if can_place_ship(self.player_primary_grid, row, col, ship_length, direction):
            place_ship(self.player_primary_grid, row, col, ship_length, direction)
            self.player_ship_placements.append((row, col, ship_length, direction))
            self.draw_ship(self.player_canvas, row, col, ship_length, direction, tag=f"player_ship_{self.current_ship_index}")

            self.current_ship_index += 1
            if self.current_ship_index < len(self.ships):
                self.instructions.config(
                    text=(
                        f"Postavi ladjico dolžine {self.ships[self.current_ship_index]} "
                        "(levi klik = navpično, desni klik = vodoravno)"
                    )
                )
            else:
                self.instructions.config(text="Vse ladjice so postavljene!")
                self.start_button.config(state="normal")
        else:
            reason = placement_block_reason(self.player_primary_grid, row, col, ship_length, direction)
            suffix = f" ({reason})" if reason else ""
            self.instructions.config(text=f"Ladjice ni mogoče postaviti tukaj{suffix}. Poskusi znova.")

    # Začni igro
    def start_game(self):
        self.instructions.config(text="Igra se je začela! Klikni na računalnikovo mrežo za streljanje.")
        self.game_started = True

        # Računalnik postavi svoje ladjice
        for ship_length in self.ships:
            while True:
                row = random.randint(0, 9)
                col = random.randint(0, 9)
                direction = random.choice(["H", "V"])
                if can_place_ship(self.computer_primary_grid, row, col, ship_length, direction):
                    place_ship(self.computer_primary_grid, row, col, ship_length, direction)
                    self.computer_ship_placements.append((row, col, ship_length, direction))
                    break

        # Računalnikove ladje ostanejo skrite; rišemo samo zadetke/zgrešene strele.

    # Igralec strelja
    def player_shoot(self, row, col):
        if self.player_target_grid[row][col] != 0:
            return  # Polje je že zadeto
        sunk_length = None
        if self.computer_primary_grid[row][col] == 1:
            self.draw_shot_marker(self.computer_canvas, self.computer_shot_markers, row, col, hit=True)
            self.player_target_grid[row][col] = 1
            self.computer_primary_grid[row][col] = -1
            sunk_length = self.mark_computer_ship_sunk(row, col)
            if sunk_length is not None:
                sunk_message = f"Potopljena računalnikova ladja dolžine {sunk_length}"
                print(sunk_message, flush=True)
                self.instructions.config(text=sunk_message)
                self.root.update_idletasks()
        else:
            self.draw_shot_marker(self.computer_canvas, self.computer_shot_markers, row, col, hit=False)
            self.player_target_grid[row][col] = -1

        if all_ships_sunk(self.computer_primary_grid):
            winner_message = "Zmagovalec: Igralec"
            print(winner_message)
            self.instructions.config(text=winner_message)
            self.disable_all_buttons()
            return

        self.waiting_for_computer_shot = True
        if sunk_length is not None:
            # Pusti sporočilo potopitve vidno na istem mestu kot navodila.
            self.root.after(3000, lambda: self.delayed_computer_shoot(preserve_message=True))
            return

        self.root.after(300, lambda: self.delayed_computer_shoot(preserve_message=False))

    def delayed_computer_shoot(self, preserve_message=False):
        try:
            self.computer_shoot(preserve_message=preserve_message)
        finally:
            self.waiting_for_computer_shot = False

    # Računalnik strelja
    def computer_shoot(self, preserve_message=False):
        if not preserve_message:
            self.instructions.config(text="Računalnik strelja...")
        while True:
            row = random.randint(0, 9)
            col = random.randint(0, 9)
            if self.computer_target_grid[row][col] == 0:
                if self.player_primary_grid[row][col] == 1:
                    self.draw_shot_marker(self.player_canvas, self.player_shot_markers, row, col, hit=True)
                    self.computer_target_grid[row][col] = 1
                    self.player_primary_grid[row][col] = -1
                    sunk_length = self.mark_player_ship_sunk(row, col)
                else:
                    self.draw_shot_marker(self.player_canvas, self.player_shot_markers, row, col, hit=False)
                    self.computer_target_grid[row][col] = -1
                    sunk_length = None
                break

        if all_ships_sunk(self.player_primary_grid):
            winner_message = "Zmagovalec: Računalnik"
            print(winner_message)
            self.instructions.config(text=winner_message)
            self.disable_all_buttons()
            return

        if sunk_length is not None:
            sunk_message = f"Potopljena ladja dolžine {sunk_length}"
            print(sunk_message)
            self.instructions.config(text=sunk_message)
            return

        if not preserve_message:
            self.instructions.config(text="Tvoj na vrsti! Klikni na računalnikovo mrežo.")

    # Onemogoči vse gumbe (po koncu igre)
    def disable_all_buttons(self):
        self.game_over = True

# Zaženi igro
if __name__ == "__main__":
    try:
        root = tk.Tk()
    except Exception as exc:
        raise SystemExit(
            "Tk GUI se ni uspel zagnati. Preveri, da imaš na voljo grafični zaslon "
            "(npr. nastavljena spremenljivka DISPLAY) in da je nameščen python3-tk."
        ) from exc

    game = BattleshipGame(root)
    root.mainloop()