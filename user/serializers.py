from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # fields = ('email', 'name', 'role')
        fields = '__all__'
    
    def update(self, instance, validated_data):
        # Extract the password from the validated_data
        password = validated_data.pop('password', None)  # Remove 'password' safely

        # Update the remaining fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)  # Hash the password and set it

        instance.save()  # Save the updates to the database
        return instance