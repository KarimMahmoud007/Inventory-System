from views.recipes_window import RecipesPage
from models.recipes_model import RecipesModel
class RecipesController:
    def __init__(self):
        super().__init__()
        self.recipes_view = RecipesPage()
        self.model = RecipesModel()
