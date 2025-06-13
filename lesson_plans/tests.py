from django.contrib.auth.models import User
from lesson_plans.models import UserProfile

# For user 'admin'
user = User.objects.get(username='admin')
UserProfile.objects.get_or_create(user=user, defaults={'role': 'admin'})

# For user 'user'
user = User.objects.get(username='client')
UserProfile.objects.get_or_create(user=user, defaults={'role': 'client'})

# from pinecone import Pinecone, ServerlessSpec


# pc = Pinecone(api_key="")

# index_name = "yourpeak-gpt"

# pc.create_index(
#         name=index_name, 
#         dimension=3072,
#         metric='cosine',
#         spec=ServerlessSpec(cloud='aws', region='us-east-1')
#     )