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
def ustvariMrezo(size=10):
    """Ustvari prazno kvadratno mrezo za igro.

    Parametri:
        size: Velikost ene stranice mreze.

    Vrne:
        Seznam seznamov z vrednostmi 0.
    """
    return [[0 for _ in range(size)] for _ in range(size)]

# Preveri, ali je ladjico možno postaviti na mrežo
def lahkoPostavisLadjo(grid, row, col, length, direction):
    """Preveri, ali je ladjo mogoce postaviti na izbrano mesto.

    Parametri:
        grid: Igralna mreza.
        row: Zacetna vrstica postavitve.
        col: Zacetni stolpec postavitve.
        length: Dolzina ladje.
        direction: Smer postavitve, 'H' ali 'V'.

    Vrne:
        True, ce je postavitev veljavna, sicer False.
    """
    if direction == "H":
        if col + length > len(grid[0]):
            return False
        return all(grid[row][col + i] == 0 for i in range(length))
    elif direction == "V":
        if row + length > len(grid):
            return False
        return all(grid[row + i][col] == 0 for i in range(length))


def razlogBlokadePostavitve(grid, row, col, length, direction):
    """Vrne razlog, zakaj ladje ni mogoce postaviti na izbrano mesto.

    Parametri:
        grid: Igralna mreza.
        row: Zacetna vrstica postavitve.
        col: Zacetni stolpec postavitve.
        length: Dolzina ladje.
        direction: Smer postavitve, 'H' ali 'V'.

    Vrne:
        Besedilni opis razloga ali None, ce je postavitev mozna.
    """
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
def postaviLadjo(grid, row, col, length, direction):
    """V mrezo zapise ladjo na podano mesto in v podani smeri.

    Parametri:
        grid: Igralna mreza.
        row: Zacetna vrstica postavitve.
        col: Zacetni stolpec postavitve.
        length: Dolzina ladje.
        direction: Smer postavitve, 'H' ali 'V'.
    """
    if direction == "H":
        for i in range(length):
            grid[row][col + i] = 1
    elif direction == "V":
        for i in range(length):
            grid[row + i][col] = 1

# Preveri, ali so vse ladjice potopljene
def vseLadjePotopljene(grid):
    """Preveri, ali na mrezi ni vec nepoškodovanih ladij.

    Parametri:
        grid: Igralna mreza, ki vsebuje stanje ladij.

    Vrne:
        True, ce so vse ladje potopljene, sicer False.
    """
    return all(cell != 1 for row in grid for cell in row)

# Glavni razred za grafični vmesnik
class IgraPotapljanje:
    """Glavni razred, ki upravlja logiko igre in graficni vmesnik."""

    def __init__(self, root):
        """Inicializira stanje igre, nalozi slike in zgradi uporabniski vmesnik.

        Parametri:
            root: Glavno Tkinter okno aplikacije.
        """
        self.root = root
        self.root.title("Potapljanje ladjic")

        # Ustvari mreži za igralca in računalnik
        self.player_primary_grid = ustvariMrezo()
        self.computer_primary_grid = ustvariMrezo()
        self.player_target_grid = ustvariMrezo()
        self.computer_target_grid = ustvariMrezo()

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
        self.fire_px = max(10, int(self.cell_px * 0.75))

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
        self.instructions_w_px = self.ui_total_w_px + 20

        # Rahlo povecaj zacetno okno in prostor za navodila, da se besedilo izpise do konca.
        self.root.geometry(f"{self.instructions_w_px}x360")
        self.root.minsize(self.instructions_w_px, 360)

        # Naloži slike ladij (ena slika čez več celic, tudi navpično).
        self.ship_images = self.naloziSlikeLadij()
        self.fire_image = self.naloziSlikoOgnja()

        # Stabilen layout: 3 stolpci (igralec | ločnica | računalnik).
        self.board_frame = tk.Frame(root)
        self.board_frame.grid(row=0, column=0, sticky="w")

        # Canvas mreži (namesto gumbov) omogočata risanje ene slike čez več celic.
        tk.Label(self.board_frame, text="Igralec").grid(row=0, column=0, padx=(self.outer_pad_x, 0), sticky="w")
        self.player_canvas = tk.Canvas(
            self.board_frame,
            width=self.board_w_px,
            height=self.board_w_px,
            highlightthickness=0,
        )
        self.player_canvas.grid(row=1, column=0, padx=(self.outer_pad_x, 0), sticky="w")
        self.narisiMrezo(self.player_canvas, water_color="blue")
        self.player_canvas.bind("<Button-1>", lambda e: self.obKlikuIgralcevegaPlatna(e, "V"))
        self.player_canvas.bind("<Button-3>", lambda e: self.obKlikuIgralcevegaPlatna(e, "H"))
        self.player_canvas.bind("<Button-2>", lambda e: self.obKlikuIgralcevegaPlatna(e, "H"))

        # Vizualna ločnica med mrežama.
        tk.Frame(self.board_frame, bg="black", width=self.separator_w_px).grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="ns",
            padx=self.separator_pad_x,
        )

        tk.Label(self.board_frame, text="Računalnik").grid(row=0, column=2, padx=(0, self.outer_pad_x), sticky="w")
        self.computer_canvas = tk.Canvas(
            self.board_frame,
            width=self.board_w_px,
            height=self.board_w_px,
            highlightthickness=0,
        )
        self.computer_canvas.grid(row=1, column=2, padx=(0, self.outer_pad_x), sticky="w")
        self.narisiMrezo(self.computer_canvas, water_color="green")
        self.computer_canvas.bind("<Button-1>", self.obKlikuRacunalnikovegaPlatna)

        # Spodnji del (navodila + gumb) ima fiksno širino in dovolj višine,
        # da se okno ne spreminja in da je gumb vedno viden.
        self.bottom_frame = tk.Frame(root, width=self.instructions_w_px, height=90)
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
            wraplength=self.instructions_w_px,
        )
        self.instructions.grid(row=0, column=0, sticky="w", padx=(self.outer_pad_x, self.outer_pad_x), pady=(6, 2))

        # Gumb za začetek igre
        self.start_button = tk.Button(self.bottom_frame, text="Začni igro", state="disabled", command=self.zacniIgro)
        self.start_button.grid(row=1, column=0, sticky="w", padx=(self.outer_pad_x, self.outer_pad_x), pady=(0, 6))

        self.player_shot_markers = {}
        self.computer_shot_markers = {}
        self.revealed_computer_ships = set()

    def narisiMrezo(self, canvas, water_color):
        """Narise ozadje mreze in vse crte mreze na podano platno.

        Parametri:
            canvas: Tkinter canvas, na katerega se rise mreza.
            water_color: Barva ozadja mreze.
        """
        canvas.delete("all")
        w = self.cell_px * 10
        h = self.cell_px * 10
        canvas.create_rectangle(0, 0, w, h, fill=water_color, outline=water_color)
        for i in range(11):
            x = i * self.cell_px
            y = i * self.cell_px
            canvas.create_line(x, 0, x, h, fill="black")
            canvas.create_line(0, y, w, y, fill="black")

    def dogodekVCelico(self, event):
        """Pretvori polozaj klika miske v koordinate celice mreze.

        Parametri:
            event: Tkinter dogodek klika miske.

        Vrne:
            Par (row, col) ali None, ce je klik izven mreze.
        """
        col = int(event.x // self.cell_px)
        row = int(event.y // self.cell_px)
        if 0 <= row < 10 and 0 <= col < 10:
            return row, col
        return None

    def obKlikuIgralcevegaPlatna(self, event, direction):
        """Obdela klik igralca pri postavljanju ladij.

        Parametri:
            event: Tkinter dogodek klika miske.
            direction: Zelena smer postavitve ladje, 'H' ali 'V'.

        Vrne:
            Niz 'break', da se dogodek ne siri naprej.
        """
        if self.game_started or self.game_over:
            return "break"

        cell = self.dogodekVCelico(event)
        if cell is None:
            self.instructions.config(text="Klik izven mreže.")
            return "break"

        row, col = cell
        try:
            # Pomaga pri diagnostiki, če klik/vezava ne deluje.
            #self.instructions.config(text=f"Klik: ({row}, {col}), smer={direction}")
            self.postaviIgralcevoLadjo(row, col, direction)
        except Exception as exc:
            self.instructions.config(text=f"Napaka pri kliku: {type(exc).__name__}: {exc}")

        return "break"

    def obKlikuRacunalnikovegaPlatna(self, event):
        """Obdela klik na racunalnikovo mrezo med igralcevo potezo.

        Parametri:
            event: Tkinter dogodek klika miske.

        Vrne:
            Niz 'break', da se dogodek ne siri naprej.
        """
        if (not self.game_started) or self.game_over or self.waiting_for_computer_shot:
            return "break"
        cell = self.dogodekVCelico(event)
        if cell is None:
            return "break"
        row, col = cell
        self.igralecStrelja(row, col)
        return "break"

    def naloziSlikeLadij(self, hit_variant=False):
        """Nalozi slike ladij in jih prilagodi velikosti mreze.

        Parametri:
            hit_variant: Ce je True, poskusi naloziti posebno varianto slike.

        Vrne:
            Slovar slik po kljucu (dolzina, smer).
        """
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

    def naloziSlikoOgnja(self):
        """Nalozi in pomanjsa sliko ognja za prikaz zadetka.

        Vrne:
            Tkinter sliko ognja ali None, ce je ni mogoce naloziti.
        """
        base_dir = Path(__file__).parent
        fire_path = base_dir / "ogenj.png"
        if not fire_path.exists():
            return None

        target_size = self.fire_px

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

    def narisiLadjo(self, canvas, row, col, ship_length, direction, tag):
        """Narise ladjo na podano platno in uredi njene sloje.

        Parametri:
            canvas: Tkinter canvas, na katerega se rise ladja.
            row: Zacetna vrstica ladje.
            col: Zacetni stolpec ladje.
            ship_length: Dolzina ladje.
            direction: Smer ladje, 'H' ali 'V'.
            tag: Oznaka elementa na platnu.
        """
        img = self.ship_images.get((ship_length, direction))
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

    def narisiOznakoStrela(self, canvas, marker_dict, row, col, hit):
        """Narise oznako strela kot ogenj ali zgreseno polje.

        Parametri:
            canvas: Tkinter canvas, na katerega se rise marker.
            marker_dict: Slovar ze narisanih markerjev.
            row: Vrstica zadetega ali zgresenega polja.
            col: Stolpec zadetega ali zgresenega polja.
            hit: True za zadetek, False za zgresen strel.
        """
        key = (row, col)
        if key in marker_dict:
            return

        pad = 2
        x1 = col * self.cell_px + pad
        y1 = row * self.cell_px + pad
        x2 = (col + 1) * self.cell_px - pad
        y2 = (row + 1) * self.cell_px - pad
        if hit and self.fire_image is not None:
            offset = (self.cell_px - self.fire_px) // 2
            image_x = col * self.cell_px + offset
            image_y = row * self.cell_px + offset
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

    def pridobiCeliceLadje(self, row, col, ship_length, direction):
        """Vrne seznam vseh celic, ki jih pokriva ladja.

        Parametri:
            row: Zacetna vrstica ladje.
            col: Zacetni stolpec ladje.
            ship_length: Dolzina ladje.
            direction: Smer ladje, 'H' ali 'V'.

        Vrne:
            Seznam koordinat celic ladje.
        """
        if direction == "H":
            return [(row, col + i) for i in range(ship_length)]
        return [(row + i, col) for i in range(ship_length)]

    def pridobiPostavitevLadjePoCelici(self, placements, row, col):
        """Poisce ladjo, ki zaseda podano celico.

        Parametri:
            placements: Seznam vseh postavitev ladij.
            row: Vrstica iskane celice.
            col: Stolpec iskane celice.

        Vrne:
            Podatke o ladji ali None, ce celica ne pripada nobeni ladji.
        """
        for idx, (ship_row, ship_col, ship_length, direction) in enumerate(placements):
            if (row, col) in self.pridobiCeliceLadje(ship_row, ship_col, ship_length, direction):
                return idx, ship_row, ship_col, ship_length, direction
        return None

    def oznaciIgralcevoPotopljenoLadjo(self, row, col):
        """Preveri, ali je bila igralceva ladja po zadetku potopljena.

        Parametri:
            row: Vrstica zadetka.
            col: Stolpec zadetka.

        Vrne:
            Dolzino potopljene ladje ali None.
        """
        ship_info = self.pridobiPostavitevLadjePoCelici(self.player_ship_placements, row, col)
        if ship_info is None:
            return None

        _, ship_row, ship_col, ship_length, direction = ship_info
        ship_cells = self.pridobiCeliceLadje(ship_row, ship_col, ship_length, direction)
        if not all(self.player_primary_grid[r][c] == -1 for r, c in ship_cells):
            return None
        return ship_length

    def oznaciRacunalnikovoPotopljenoLadjo(self, row, col):
        """Preveri, ali je bila racunalnikova ladja potopljena, in jo razkrije.

        Parametri:
            row: Vrstica zadetka.
            col: Stolpec zadetka.

        Vrne:
            Dolzino potopljene ladje ali None.
        """
        ship_info = self.pridobiPostavitevLadjePoCelici(self.computer_ship_placements, row, col)
        if ship_info is None:
            return None

        idx, ship_row, ship_col, ship_length, direction = ship_info
        if idx in self.revealed_computer_ships:
            return None

        ship_cells = self.pridobiCeliceLadje(ship_row, ship_col, ship_length, direction)
        if not all(self.computer_primary_grid[r][c] == -1 for r, c in ship_cells):
            return None

        sunk_tag = f"computer_ship_sunk_{idx}"
        self.computer_canvas.delete(sunk_tag)
        base_img = self.ship_images.get((ship_length, direction))
        x = ship_col * self.cell_px
        y = ship_row * self.cell_px
        if base_img is not None:
            self.computer_canvas.create_image(x, y, image=base_img, anchor="nw", tags=(sunk_tag, "ship"))
        if base_img is None:
            if direction == "H":
                self.computer_canvas.create_rectangle(
                    x,
                    y,
                    x + ship_length * self.cell_px,
                    y + self.cell_px,
                    fill="darkgreen",
                    outline="black",
                    width=2,
                    tags=(sunk_tag, "ship"),
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
                    tags=(sunk_tag, "ship"),
                )

        self.computer_canvas.tag_raise("shot")
        self.computer_canvas.tag_lower("shot_under", "ship")
        self.revealed_computer_ships.add(idx)
        return ship_length

    # Postavi ladjico igralca
    def postaviIgralcevoLadjo(self, row, col, direction):
        """Poskusi postaviti trenutno igralcevo ladjo na izbrano mesto.

        Parametri:
            row: Zacetna vrstica postavitve.
            col: Zacetni stolpec postavitve.
            direction: Smer postavitve ladje, 'H' ali 'V'.
        """
        if self.current_ship_index >= len(self.ships):
            return

        ship_length = self.ships[self.current_ship_index]

        if lahkoPostavisLadjo(self.player_primary_grid, row, col, ship_length, direction):
            postaviLadjo(self.player_primary_grid, row, col, ship_length, direction)
            self.player_ship_placements.append((row, col, ship_length, direction))
            self.narisiLadjo(self.player_canvas, row, col, ship_length, direction, tag=f"player_ship_{self.current_ship_index}")

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
            reason = razlogBlokadePostavitve(self.player_primary_grid, row, col, ship_length, direction)
            suffix = f" ({reason})" if reason else ""
            self.instructions.config(text=f"Ladjice ni mogoče postaviti tukaj{suffix}. Poskusi znova.")

    # Začni igro
    def zacniIgro(self):
        """Zacne igro in nakljucno postavi vse racunalnikove ladje."""
        self.instructions.config(text="Igra se je začela! Klikni na računalnikovo mrežo za streljanje.")
        self.game_started = True

        # Računalnik postavi svoje ladjice
        for ship_length in self.ships:
            while True:
                row = random.randint(0, 9)
                col = random.randint(0, 9)
                direction = random.choice(["H", "V"])
                if lahkoPostavisLadjo(self.computer_primary_grid, row, col, ship_length, direction):
                    postaviLadjo(self.computer_primary_grid, row, col, ship_length, direction)
                    self.computer_ship_placements.append((row, col, ship_length, direction))
                    break

        # Računalnikove ladje ostanejo skrite; rišemo samo zadetke/zgrešene strele.

    # Igralec strelja
    def igralecStrelja(self, row, col):
        """Izvede igralcev strel na racunalnikovo mrezo.

        Parametri:
            row: Vrstica ciljanega polja.
            col: Stolpec ciljanega polja.
        """
        if self.player_target_grid[row][col] != 0:
            return  # Polje je že zadeto
        sunk_length = None
        if self.computer_primary_grid[row][col] == 1:
            self.narisiOznakoStrela(self.computer_canvas, self.computer_shot_markers, row, col, hit=True)
            self.player_target_grid[row][col] = 1
            self.computer_primary_grid[row][col] = -1
            sunk_length = self.oznaciRacunalnikovoPotopljenoLadjo(row, col)
            if sunk_length is not None:
                sunk_message = f"Potopljena računalnikova ladja dolžine {sunk_length}"
                print(sunk_message, flush=True)
                self.instructions.config(text=sunk_message)
                self.root.update_idletasks()
        else:
            self.narisiOznakoStrela(self.computer_canvas, self.computer_shot_markers, row, col, hit=False)
            self.player_target_grid[row][col] = -1

        if vseLadjePotopljene(self.computer_primary_grid):
            winner_message = "Zmagovalec: Igralec"
            print(winner_message)
            self.instructions.config(text=winner_message)
            self.onemogociVseGumbe()
            return

        self.waiting_for_computer_shot = True
        if sunk_length is not None:
            # Pusti sporočilo potopitve vidno na istem mestu kot navodila.
            self.root.after(3000, lambda: self.zakasnjenRacunalnikovStrel(preserve_message=True))
            return

        self.root.after(300, lambda: self.zakasnjenRacunalnikovStrel(preserve_message=False))

    def zakasnjenRacunalnikovStrel(self, preserve_message=False):
        """Z zamikom sprozi racunalnikov strel in sprosti cakanje na potezo.

        Parametri:
            preserve_message: Ce je True, ohrani trenutno sporocilo navodil.
        """
        try:
            self.racunalnikStrelja(preserve_message=preserve_message)
        finally:
            self.waiting_for_computer_shot = False

    # Računalnik strelja
    def racunalnikStrelja(self, preserve_message=False):
        """Izvede racunalnikov nakljucni strel na igralcevo mrezo.

        Parametri:
            preserve_message: Ce je True, ne prepisuje trenutnega navodila.
        """
        if not preserve_message:
            self.instructions.config(text="Računalnik strelja...")
        while True:
            row = random.randint(0, 9)
            col = random.randint(0, 9)
            if self.computer_target_grid[row][col] == 0:
                if self.player_primary_grid[row][col] == 1:
                    self.narisiOznakoStrela(self.player_canvas, self.player_shot_markers, row, col, hit=True)
                    self.computer_target_grid[row][col] = 1
                    self.player_primary_grid[row][col] = -1
                    sunk_length = self.oznaciIgralcevoPotopljenoLadjo(row, col)
                else:
                    self.narisiOznakoStrela(self.player_canvas, self.player_shot_markers, row, col, hit=False)
                    self.computer_target_grid[row][col] = -1
                    sunk_length = None
                break

        if vseLadjePotopljene(self.player_primary_grid):
            winner_message = "Zmagovalec: Računalnik"
            print(winner_message)
            self.instructions.config(text=winner_message)
            self.onemogociVseGumbe()
            return

        if sunk_length is not None:
            sunk_message = f"Potopljena ladja dolžine {sunk_length}"
            print(sunk_message)
            self.instructions.config(text=sunk_message)
            return

        if not preserve_message:
            self.instructions.config(text="Tvoj na vrsti! Klikni na računalnikovo mrežo.")

    # Onemogoči vse gumbe (po koncu igre)
    def onemogociVseGumbe(self):
        """Oznaci igro kot zakljuceno in onemogoci nadaljnje poteze."""
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

    game = IgraPotapljanje(root)
    root.mainloop()