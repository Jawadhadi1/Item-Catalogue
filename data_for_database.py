from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import User, Supermarket, Item, Base

engine = create_engine('sqlite:///supermarketwithusers.db')


# Bind the engine to the metadata of the Base class so that it becomes
# possible to acess the declaratives through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)


# A DBSession() instance establishes all communications with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't get written into the database until session.commit() is called.
session = DBSession()

# Create a user
Alex1 = User(name="Alex Crawford", email="alex_craw@hotmail.com.com",
             picture='http://img2.wikia.nocookie.net/__cb20091111204212/disney/images/4/45/Goofy_hq.png')
session.add(Alex1)
session.commit()

# Items in Kaufland supermarket
supermarket_1 = Supermarket(user_id=8, name="Kaufland")

session.add(supermarket_1)
session.commit()


Item_1 = Item(user_id=8, name="asian spicy noodles", description="Hearty noodles with the unique taste from Asia",
                     price="$4.99", supermarket=supermarket_1)

session.add(Item_1)
session.commit()

Item_2 = Item(user_id=8, name="chicken soup", description="Delicious soup made of chcken", price="$7", supermarket=supermarket_1)

session.add(Item_2)
session.commit()

# Items in Aldi supermarket
supermarket_2 = Supermarket(user_id=8, name="Aldi")

session.add(supermarket_2)
session.commit()


Item_1 = Item(user_id=8, name="tortilla pringles", description="Tasty chips made from potatoes",
                     price="$2.99", supermarket=supermarket_2)

session.add(Item_1)
session.commit()

Item_2 = Item(user_id=8, name="Dr Oetker Pizza", description="Delicious chicken pizza prepared in oven", price="$5", supermarket=supermarket_2)

session.add(Item_2)
session.commit()
