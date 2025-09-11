from packages.backend.sql_connection import users, database as db

pool = db.create_pool()
connection = pool.getconn()
cursor = connection.cursor()

# hashing the password
password = hash_pwd("TestPassword123")

# adding a user
"""result = users.add_user(connection=connection,
               cursor=cursor,
               user_role=users.UserRole.GUEST,
               room="321",
               residence=users.Residence.ALTBAU,
               first_name="Leon",
               last_name="Gattermeyer",
               email=users.Email("lpwgfs@gmail.com"),
               password_hash=password,
               returning="id")
print(result)"""

# testing whether program actually stops adding a user with faulty data

# double email
# adding a user
result = users.add_user(connection=connection,
                        cursor=cursor,
                        user_role=users.UserRole.GUEST,
                        room="321",
                        residence=users.Residence.ALTBAU,
                        first_name="Leon",
                        last_name="Gattermeyer",
                        email=users.Email("lpwgfs@gmail.com"),
                        password_hash=password,
                        returning="id")
print(result)

"""result = users.remove_user(connection=connection,
               cursor=cursor,
               user_id=result["id"])
print(result)"""

# print(match_pwd("TestPassword123", "$2b$12$sUtWqHFTKxWr2P7M6L4tMeiL4pqoykIo4pbshkSqFY97gP6er8sny"))

"""result = users.remove_user(connection=connection,
               cursor=cursor,
               user_id=1)
print(result)"""
