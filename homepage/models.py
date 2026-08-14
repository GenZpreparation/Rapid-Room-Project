from django.db import models


# Create your models here.
class user(models.Model):
    name=models.CharField(max_length=200)
    email=models.CharField(max_length=200, unique=True) # Ensure emails are unique across all users
    password=models.CharField(max_length=255) # Store hashed passwords
    
    ROLE_CHOICES = [
        ('owner', 'Room Owner'),
        ('student', 'Student/Tenant'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')

    # Student-specific fields (nullable for owners)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    dob = models.DateField(null=True, blank=True)

    # New Owner-specific profile fields (can also be used by students if needed)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    landmark = models.CharField(max_length=255, null=True, blank=True)

    # New Student-specific profile fields
    hometown = models.CharField(max_length=100, null=True, blank=True)
    PREFERRED_ROOM_CHOICES = [
        ('single', 'Single Room'),
        ('shared', 'Shared Room'),
        ('pg', 'PG / Paying Guest'),
        ('hostel', 'Hostel'),
    ]
    preferred_room_type = models.CharField(max_length=10, choices=PREFERRED_ROOM_CHOICES, null=True, blank=True)

class Post(models.Model):
    author = models.ForeignKey(user, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # New fields for more detail
    street_address = models.CharField(max_length=255, default='')
    city = models.CharField(max_length=100, default='')
    state = models.CharField(max_length=100, default='')
    postal_code = models.CharField(max_length=10, default='')
    area = models.PositiveIntegerField(default=0) # Area in sq. ft.
    ROOM_TYPE_CHOICES = [
        ('private', 'Private Room'),
        ('shared', 'Shared Room'),
        ('apartment', 'Full Apartment'),
    ]
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES, default='private')
    contact_number = models.CharField(max_length=15, default='')
    is_available = models.BooleanField(default=True)

    rent = models.DecimalField(max_digits=8, decimal_places=2)
    available_from = models.DateField()
    amenities = models.CharField(max_length=500) # Will store as a comma-separated string
    created_at = models.DateTimeField(auto_now_add=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    def __str__(self):
        return self.title

class PostImage(models.Model):
    post = models.ForeignKey(Post, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='post_images/')

class Tenancy(models.Model): # Renamed related_name for clarity as there can be multiple tenancies
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='tenancies_history')
    tenant = models.ForeignKey(user, on_delete=models.SET_NULL, null=True, related_name='tenancies')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True) # Can be set when tenancy ends
    is_active = models.BooleanField(default=True) # New field to track status

    def __str__(self):
        status = "Active" if self.is_active else "Ended"
        return f"{self.tenant.name} in {self.post.title}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    student = models.ForeignKey(user, on_delete=models.CASCADE, related_name='bookings')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookings')
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A student can only book a specific post once while the booking is pending or accepted
        unique_together = ('student', 'post')

    def __str__(self):
        return f"Booking for {self.post.title} by {self.student.name}"

class SavedPost(models.Model):
    student = models.ForeignKey(user, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A student can only save a specific post once
        unique_together = ('student', 'post')

    def __str__(self):
        return f"{self.student.name} saved {self.post.title}"

class Review(models.Model):
    RATING_CHOICES = [(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reviews')
    student = models.ForeignKey(user, on_delete=models.CASCADE, related_name='reviews_given')
    rating = models.PositiveIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'post') # A student can only review a post once

    def __str__(self):
        return f"Review for {self.post.title} by {self.student.name}"

class Conversation(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='conversations')
    participants = models.ManyToManyField(user, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation about {self.post.title}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(user, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(user, related_name='read_messages', blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.name} at {self.created_at}"

class RentPayment(models.Model):
    tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name='payments')
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')], default='unpaid')
    paid_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"Rent for {self.due_date.strftime('%B %Y')} for tenancy {self.tenancy.id}"

class MaintenanceRequest(models.Model):
    PRIORITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    STATUS_CHOICES = [('submitted', 'Submitted'), ('in_progress', 'In Progress'), ('completed', 'Completed')]
    
    tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name='maintenance_requests')
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    image = models.ImageField(upload_to='maintenance_photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request for {self.tenancy.post.title}: {self.title}"

class MaintenanceComment(models.Model):
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(user, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.name} on request {self.request.id}"
