from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QScrollArea, QGridLayout, QVBoxLayout,
    QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QSize, Signal



# ----------------------------------------------------------------- #
#  Single Recipe Card
# ------------------------------------------------------------------ #
class RecipeCard(QFrame):
    """
    A card widget showing a recipe thumbnail + title + ingredients list.

    Signals
    -------
    add_clicked(id: int)   -- user pressed the green Add button
    edit_clicked(id: int)  -- user pressed the orange Edit button
    """

    add_clicked  = Signal(int)
    edit_clicked = Signal(int)

    def __init__(self, id: int = 0, title: str = "", ingredients: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.id = id
        self.title       = title
        self.ingredients = ingredients or []
        self._build_ui()
        self._apply_style()

    # -- layout --------------------------------------------------------
    def _build_ui(self):
        self.setFixedSize(QSize(180, 248))
        self.setFrameShape(QFrame.Shape.Box)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header band
        self.header = QFrame()
        self.header.setFixedHeight(80)
        self.header.setObjectName("cardHeader")

        header_layout = QVBoxLayout(self.header)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName("cardTitle")
        header_layout.addWidget(self.title_label)

        # body (ingredients)
        self.body = QFrame()
        self.body.setObjectName("cardBody")

        body_layout = QVBoxLayout(self.body)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        body_layout.setContentsMargins(10, 8, 10, 4)
        body_layout.setSpacing(3)

        for ing in self.ingredients:
            lbl = QLabel(f"- {ing}")
            lbl.setObjectName("ingredientItem")
            body_layout.addWidget(lbl)

        if not self.ingredients:
            body_layout.addWidget(QLabel(""))

        # footer (Add + Edit buttons)
        self.footer = QFrame()
        self.footer.setFixedHeight(40)
        self.footer.setObjectName("cardFooter")

        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(8, 5, 8, 5)
        footer_layout.setSpacing(8)



        self.edit_btn = QPushButton("/ Edit")
        self.edit_btn.setObjectName("cardEditBtn")
        self.edit_btn.setFixedHeight(26)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.setToolTip("Edit this recipe")
        self.edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.id))


        footer_layout.addWidget(self.edit_btn)

        root.addWidget(self.header)
        root.addWidget(self.body, 1)
        root.addWidget(self.footer)

    # -- style ---------------------------------------------------------
    def _apply_style(self):
        self.setStyleSheet("""
            RecipeCard {
                background: #FFFDF7;
                border: 2px solid #D64545;
                border-radius: 10px;
            }

            QFrame#cardHeader {
                background: #FAE8E0;
                border-top-left-radius:  8px;
                border-top-right-radius: 8px;
                border-bottom: 2px solid #D64545;
            }
            QLabel#cardTitle {
                font-family: Georgia;
                font-size: 13px;
                font-weight: bold;
                color: #2C1810;
                padding: 4px;
            }

            QFrame#cardBody {
                background: #FFFDF7;
            }
            QLabel#ingredientItem {
                font-family: Georgia;
                font-size: 11px;
                color: #4A3728;
            }

            QFrame#cardFooter {
                background: #FFF0E8;
                border-top: 1px solid #E8C4B0;
                border-bottom-left-radius:  8px;
                border-bottom-right-radius: 8px;
            }
            QPushButton#cardAddBtn:hover   { background: #27874E; }
            QPushButton#cardAddBtn:pressed { background: #1E6B3E; }

            QPushButton#cardEditBtn {
                font-family: Georgia;
                font-size: 10px;
                font-weight: bold;
                color: #FFFFFF;
                background: #D67C2A;
                border: none;
                border-radius: 5px;
                padding: 0 6px;
            }
            QPushButton#cardEditBtn:hover   { background: #B86820; }
            QPushButton#cardEditBtn:pressed { background: #955318; }
        """)

    # -- hover border glow ---------------------------------------------
    def enterEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace(
            "border: 2px solid #D64545;",
            "border: 2px solid #FF6B35;"
        ))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace(
            "border: 2px solid #FF6B35;",
            "border: 2px solid #D64545;"
        ))
        super().leaveEvent(event)


# ------------------------------------------------------------------ #
#  Recipes Page
# ------------------------------------------------------------------ #
class RecipesPage(QWidget):
    """
    Main recipes view -- a grid of RecipeCard widgets with a header bar.
    Pass `recipes` as a list of dicts: [{"title": ..., "ingredients": [...]}]
    """

    add_recipe_requested = Signal()
    edit_recipe_requested = Signal(int)

    COLUMNS      = 4
    CARD_SPACING = 18

    def __init__(self, recipes: list[dict] | None = None, parent=None):
        super().__init__(parent)
        self.recipes = recipes or []
        self.setWindowTitle("Recipes")
        self.setMinimumSize(900, 650)
        self._build_ui()
        self._apply_style()
        self._populate_cards()

    # -- layout --------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        # top bar
        top_bar = QHBoxLayout()

        self.page_title = QLabel("Recipes")
        self.page_title.setObjectName("pageTitle")

        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("addBtn")
        self.add_btn.setFixedSize(42, 42)
        self.add_btn.setToolTip("Add new recipe")
        self.add_btn.clicked.connect(self._on_add_clicked)

        top_bar.addWidget(self.page_title)
        top_bar.addStretch()
        top_bar.addWidget(self.add_btn)
        root.addLayout(top_bar)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        # scrollable card grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("scrollArea")

        self.grid_container = QWidget()
        self.grid_container.setObjectName("gridContainer")

        self.card_grid = QGridLayout(self.grid_container)
        self.card_grid.setSpacing(self.CARD_SPACING)
        self.card_grid.setContentsMargins(4, 8, 4, 8)
        self.card_grid.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        scroll.setWidget(self.grid_container)
        root.addWidget(scroll, 1)

    # -- populate ------------------------------------------------------
    def _populate_cards(self):
        while self.card_grid.count():
            item = self.card_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, recipe in enumerate(self.recipes):
            card = RecipeCard(
                id = recipe["id"],
                title=recipe.get("title", ""),
                ingredients=recipe.get("ingredients", [])
            )
            card.add_clicked.connect(self._on_card_add)
            card.edit_clicked.connect(self._on_card_edit)
            row, col = divmod(i, self.COLUMNS)
            self.card_grid.addWidget(card, row, col)

        # ghost cards to fill last row
        total     = len(self.recipes)
        remainder = total % self.COLUMNS
        if remainder:
            for j in range(self.COLUMNS - remainder):
                ghost = RecipeCard()

                ghost.edit_btn.hide()
                self.card_grid.addWidget(
                    ghost, total // self.COLUMNS, remainder + j
                )

    # -- style ---------------------------------------------------------
    def _apply_style(self):
        self.setStyleSheet("""
            RecipesPage {
                background: #FFF8F0;
            }
            QLabel#pageTitle {
                font-family: 'Palatino Linotype', 'Book Antiqua', Georgia, serif;
                font-size: 36px;
                font-weight: bold;
                color: #8B4FCB;
                letter-spacing: 1px;
            }
            QPushButton#addBtn {
                font-size: 22px;
                font-weight: bold;
                color: #2C1810;
                background: #FFFDF7;
                border: 2px solid #2C1810;
                border-radius: 8px;
            }
            QPushButton#addBtn:hover {
                background: #FAE8E0;
                border-color: #D64545;
                color: #D64545;
            }
            QPushButton#addBtn:pressed {
                background: #D64545;
                color: #FFFDF7;
            }
            QFrame#separator {
                color: #E8C4B0;
                max-height: 1px;
            }
            QScrollArea#scrollArea  { background: transparent; }
            QWidget#gridContainer   { background: transparent; }
        """)

    # -- slots ---------------------------------------------------------
    def _on_add_clicked(self):
        self.add_recipe_requested.emit()

    def _on_card_add(self, id: int):
        """Green Add button on a card -- override or connect externally."""
        print(f"Card Add: '{id}'")

    def _on_card_edit(self, id: int):
        """Orange Edit button on a card -- override or connect externally."""
        self.edit_recipe_requested.emit(id)

    # -- public API ----------------------------------------------------
    def set_recipes(self, recipes: list[dict]):
        """Replace the full recipe list and refresh the grid."""
        self.recipes = recipes
        self._populate_cards()

    def add_recipe(self, recipe: dict):
        """Append one recipe and refresh."""
        self.recipes.append(recipe)
        self._populate_cards()

