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
    A card widget showing a recipe title + ingredients list.

    Signals
    -------
    edit_clicked(id: int)  -- user pressed the Edit button
    """

    edit_clicked = Signal(int)

    def __init__(self, id: int = 0, title: str = "", ingredients: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.id = id
        self.title       = title
        self.ingredients = ingredients or []
        self._build_ui()

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



# ------------------------------------------------------------------ #
#  Recipes Page
# ------------------------------------------------------------------ #
class RecipesWindow(QWidget):
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


    # -- slots ---------------------------------------------------------
    def _on_add_clicked(self):
        self.add_recipe_requested.emit()

    def _on_card_edit(self, id: int):
        self.edit_recipe_requested.emit(id)

    # -- public API ----------------------------------------------------
    def set_recipes(self, recipes: list[dict]):
        """Replace the full recipe list and refresh the grid."""
        self.recipes = recipes
        self._populate_cards()

