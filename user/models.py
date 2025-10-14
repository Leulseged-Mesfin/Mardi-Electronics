from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager



class UserAccountManager(BaseUserManager):
    def create_user(self, email, name, password=None, role=None):
        if not email:
            raise ValueError('Users must have an email address.')

        email = self.normalize_email(email)
        email = email.lower()

        user = self.model(
            email = email,
            name = name,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user
    

    # def create_manager(self, email, name, password=None, role=None):
    #     user = self.create_user(email, name, password, role)

    #     # user.is_manager = True
    #     # user.role='Manager'
    #     user.save(using=self._db)
    #     return user
    
         
    def create_stuff(self, email, name, password, role):
        user = self.create_user(email, name, password, role)
        user.role=role
        user.set_password(password)
        user.save(using=self._db)
        return user


    def create_superuser(self, email, name, password=None):
        user = self.create_user(email, name, password)

        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
         


class UserAccount(AbstractBaseUser, PermissionsMixin):
    gender_category=(
        ('Male','Male'),
        ('Female','Female'),
    )
    user_roles = (
        ('Manager', 'Manager'),
        ('Salesman', 'Salesman'),
        ('Sales Manager', 'Sales Manager'),
    )

    email = models.EmailField(verbose_name='email', max_length=255, unique=True)
    name = models.CharField(max_length=255)  
    role = models.CharField(max_length=20, choices=user_roles, null=False, blank=False)
    address = models.CharField(max_length=255, null=True,blank=True)
    mobile = models.CharField(max_length=255, null=True,blank=True)
    is_active = models.BooleanField(default=True)    
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    emp_no=models.CharField(max_length=100,null=True,blank=True)
    gender=models.CharField(max_length=100,null=True, blank=True, choices=gender_category)
    age= models.IntegerField(default='0', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    profile_image = models.ImageField(upload_to='user/', null=True,blank=True)

    # is_manager = models.BooleanField(default=False)    
    # is_salesman = models.BooleanField(default=False)    

    objects = UserAccountManager()

    USERNAME_FIELD = 'email' # this is what i want them to login with
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email