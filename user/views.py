from django.contrib.auth import get_user_model
User = get_user_model()
from .serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.contrib.auth.hashers import check_password
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema


class UserListCreateAPIView(APIView):
    # permission_classes = (permissions.AllowAny,)   

    # @swagger_auto_schema(
    #     operation_description="A sample API view that requires JWT",
    # )
    def get(self, request, format=None):
        try:
            user = request.user
            if not (user.role == 'Manager' or user.is_superuser == True):
                return Response(
                    {"error": "You are not authorized to retrive the User."},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Check if the user is a manager
            if user.role == 'Manager':
                # Exclude superusers for managers
                users = User.objects.filter(is_superuser=False)
            else:
                # Retrieve all users for non-managers and non-salesman
                users = User.objects.all()
            # user = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
                
        except:
            return Response(
                {"error": "An error occurred while retriving User Detail."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                
            )

    def post(self, request):
        try:
            user = request.user
            if not (user.role == 'Manager' or user.is_superuser):
                return Response(
                    {"error": "You are not authorized to create the User."},
                    status=status.HTTP_403_FORBIDDEN
                )

            data = request.data
            name = data.get('name')
            email = data.get('email', '').lower()
            password = data.get('password')
            re_password = data.get('re_password')
            role = data.get('role')

            if not all([name, email, password, re_password, role]):
                print("All fields are required.")
                return Response(
                    {"error": "All fields are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if password != re_password:
                print("Passwords do not match.")
                return Response(
                    {"error": "Passwords do not match."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if len(password) < 8:
                print("Password should be at least 8 characters long.")
                return Response(
                    {"error": "Password should be at least 8 characters long."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if User.objects.filter(email=email).exists():
                print("User with this email already exists.")
                return Response(
                    {"error": "User with this email already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            User.objects.create_stuff(email, name, password, role)
            return Response(
                {"message": f"{user.role} account created successfully."},
                status=status.HTTP_201_CREATED
            )
           
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"})


class UserRetrieveUpdateDeleteAPIView(APIView):
    # permission_classes = (permissions.AllowAny,)

    def get(self, request, pk):
        try:
            user = request.user
            if not (user.role == 'Manager' or user.is_superuser == True):
                return Response(
                    {"error": "You are not authorized to retrive the User."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if not User.objects.filter(id=pk).exists():
                return Response(
                    {"error": "User Does not Exist."},
                    status=status.HTTP_404_NOT_FOUND
                )
            user = User.objects.get(id=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)      
        except KeyError as e:
            return Response(
                {"error": f"An error occurred while Retriving the User.  {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        try:
            user = request.user
            if not (user.role == 'Manager' or user.is_superuser == True):
                return Response(
                    {"error": "You are not authorized to update the User."},
                    status=status.HTTP_403_FORBIDDEN
                ) 

            users = User.objects.filter(id=pk).first() 
            if not users:
                return Response(
                    {"error": "User Does not Exist."},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = UserSerializer(users, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data
            serializer.update(users, validated_data)
            return Response({"message": f"{user.role} account Updated successfully."}, status=status.HTTP_200_OK)
     
        except KeyError as e:
            return Response(
                {"error": f"An error occurred while updating the User.  {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, pk):
        try:
            user = request.user
            if not (user.role == 'Manager' or user.is_superuser == True):
                return Response(
                    {"error": "You are not authorized to delete the User."},
                    status=status.HTTP_403_FORBIDDEN
                )              
            print(user.role)
            if not User.objects.filter(id=pk).exists():
                return Response(
                    {"error": "User Does not Exist."},
                    status=status.HTTP_404_NOT_FOUND
                )
            User.objects.get(id=pk).delete()
            if not User.objects.filter(id=pk).exists():
                return Response({"message": f"{user.role} account Deleted successfully."},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {"error": "Failed to delete an User."},
                    status=status.HTTP_400_BAD_REQUEST
                )
    
        except KeyError as e:
            return Response(
                {"error": f"An error occurred while deleting the User.  {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class UserProfileView(APIView):
    # permission_classes = (permissions.AllowAny,)
    def get(self, request, format=None):
        try:
            user = request.user
            users = UserSerializer(user)
            
            return Response(
                {'data': users.data},
                status=status.HTTP_200_OK
            )

        except KeyError as e:
            return Response(
                {"error": f"An error occurred while retriving Profile. {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR               
            )
    
    def patch(self, request, format=None):
        try:
            user = request.user
            serializer = UserSerializer(user, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        except:
            return Response(
                {"error": "An error occurred while updating User Detail."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserChangePassword(APIView):
    def get(self, request, *args, **kwargs):
        # permission_classes = (permissions.AllowAny,) 
        user = request.user  # This gives the actual User model instance
        if not user.is_authenticated:
            return Response(
                {"error": "User is not authenticated."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return Response({"message": "GET request is working"}, status=200)
    def post(self, request, format=None):
        try:
            user = request.user  # This gives the actual User model instance
            if not user.is_authenticated:
                return Response(
                    {"error": "User is not authenticated."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            data = request.data
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')

            if not all([current_password, new_password, confirm_password]):
                return Response(
                    {"error": "All fields are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not check_password(current_password, user.password):
                # If the password is not correct, return 400
                # user_data = UserSerializer(user).data
                return Response({"error": "Password is not correct."}, status=status.HTTP_400_BAD_REQUEST)


            if len(new_password) < 8:
                return Response(
                    {"error": "Password should be at least 8 characters long."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_password != confirm_password:
                return Response(
                    {"error": "Passwords do not match."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not new_password:
                return Response(
                    {"error": "New password is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)  # This will hash the password
            user.save()

            return Response(
                {'password': f"password is chenged successfully"},
                status=status.HTTP_200_OK
            )

        except:
            return Response(
                {"error": "An error occurred while changing Password."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR               
            )

# create a model called user and fields are email, name, password and role ,
#  role is choice and define the choice inside the user model not on its 
#  own and also create registration view and use APIView.