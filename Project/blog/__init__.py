from .views import app
from .models import graph

# Uncomment the lines below the first time you run this application, then recomment thereafter.
# Uniqueness constraints can only be made once.

#graph.schema.create_uniqueness_constraint("User", "username")
#graph.schema.create_uniqueness_constraint("Tag", "name")
#graph.schema.create_uniqueness_constraint("Question", "id")
#graph.schema.create_uniqueness_constraint("Answer", "id")
