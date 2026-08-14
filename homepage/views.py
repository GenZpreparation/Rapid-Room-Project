from django.shortcuts import render, redirect
from .models import user, Post, PostImage, Tenancy, Booking, SavedPost, Review, Conversation, Message, RentPayment, MaintenanceRequest, MaintenanceComment
from django.contrib.auth.hashers import make_password, check_password
import datetime # Import for DOB parsing
from django.urls import reverse, reverse_lazy
from django.db.models import Q, Avg, Exists, OuterRef
from django.contrib import messages
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from dateutil.relativedelta import relativedelta

def home(request):
    if request.method=='POST':
        email = request.POST.get('username') # The form uses 'username' for the email field
        password = request.POST.get('password')  
        role_type = request.POST.get('role_type') # Get role from the submitted form

        try:
            user_obj = user.objects.get(email=email)
            if check_password(password, user_obj.password):
                if user_obj.role != role_type:
                    messages.error(request, f"This account is for a {user_obj.role}. Please use the correct login section.")
                    return render(request, 'home.html')

                # Store user ID in session to mark them as logged in
                request.session['user_id'] = user_obj.id
                request.session['user_role'] = user_obj.role
                return redirect('dashboard') # Redirect to the new dashboard page
            else:
                messages.error(request, "Invalid email or password.")
        except user.DoesNotExist:
            messages.error(request, "Invalid email or password.")

    return render(request,'home.html')

def register_owner(request):
    if request.method=='POST':
        na=request.POST['full_name']
        email=request.POST['email']
        password=request.POST['password1']
        password2=request.POST['password2']

        # --- Add password confirmation ---
        if password != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('home page')
        
        if user.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('home page')

        hashed_password = make_password(password)
        obj = user(
            name=na,
            email=email,
            password=hashed_password,
            role='owner'
        )
        obj.save()
        
        messages.success(request, "Owner account created successfully! Please log in.")
        return redirect(f"{reverse('home page')}?from=owner")
    return redirect('home page') # Redirect GET requests or failed POSTs

def dashboard(request):
    # Check if the user is logged in by looking for 'user_id' in the session
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id:
        # If not logged in, redirect to the login page
        return redirect('home page')
    
    try:
        # Get the logged-in user's data to display on the page
        current_user = user.objects.get(id=user_id)
        search_query = request.GET.get('q', '') # Get search query, default to empty string
        posts_to_display = Post.objects.none() # Start with an empty queryset
        saved_post_ids = [] # Initialize for all roles
        amenities_filter = [] # Initialize for all roles
        city_filter, room_type_filter, min_rent_filter, max_rent_filter = '', '', '', '' # Initialize filters
        unread_message_count = 0

        if user_role == 'owner':
            # Owners see their own posts, newest first.
            # prefetch_related('images') is a performance optimization.
            posts_to_display = Post.objects.filter(author=current_user).order_by('-created_at').prefetch_related('images')
        elif user_role == 'student':
            # Students see all available posts, which can be filtered.
            posts_to_display = Post.objects.filter(is_available=True).order_by('-created_at').prefetch_related('images')
            
            # Get a list of post IDs that the current student has saved
            saved_post_ids = SavedPost.objects.filter(student_id=user_id).values_list('post_id', flat=True)


            amenities_filter = request.GET.getlist('amenities')
            city_filter = request.GET.get('city', '')
            room_type_filter = request.GET.get('room_type', '')
            min_rent_filter = request.GET.get('min_rent', '')
            max_rent_filter = request.GET.get('max_rent', '')

            # Get filter parameters from the request
            if search_query:
                posts_to_display = posts_to_display.filter(
                    Q(title__icontains=search_query) | Q(description__icontains=search_query)
                )
            
            if city_filter:
                posts_to_display = posts_to_display.filter(city__iexact=city_filter)

            if room_type_filter:
                posts_to_display = posts_to_display.filter(room_type=room_type_filter)

            if min_rent_filter:
                try:
                    posts_to_display = posts_to_display.filter(rent__gte=float(min_rent_filter))
                except ValueError:
                    pass # Ignore if not a valid number

            if max_rent_filter:
                try:
                    posts_to_display = posts_to_display.filter(rent__lte=float(max_rent_filter))
                except ValueError:
                    pass # Ignore if not a valid number
            
            for amenity in amenities_filter:
                posts_to_display = posts_to_display.filter(amenities__icontains=amenity)

        # Get unread message count for the sidebar badge
        unread_message_count = Message.objects.filter(
            conversation__participants=current_user
        ).exclude(
            sender=current_user
        ).exclude(
            read_by=current_user
        ).count()

    except user.DoesNotExist:
        return redirect('home page') # If user somehow doesn't exist, log them out

    context = {
    
        'user': current_user,
        'posts': posts_to_display,
        'user_role': user_role,
        'search_query': search_query, # Pass the query back to the template
        # Pass filter values back to the template
        'city_filter': city_filter,
        'room_type_filter': room_type_filter,
        'min_rent_filter': min_rent_filter,
        'max_rent_filter': max_rent_filter,
        'amenities_filter': amenities_filter,
        'saved_post_ids': saved_post_ids,
        'unread_message_count': unread_message_count,
        # Provide a list of unique cities for the dropdown
        'cities': Post.objects.filter(is_available=True).values_list('city', flat=True).distinct().order_by('city'),
        # Provide all possible amenities for the filter checkboxes
        'all_amenities': ['wifi', 'kitchen', 'ac', 'laundry', 'parking', 'furnished'],
    }

    return render(request, 'dashboard.html', context)

def owner_profile_setup(request):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id or user_role != 'owner':
        messages.error(request, "You must be logged in as an owner to access this page.")
        return redirect('home page')

    try:
        owner = user.objects.get(id=user_id)
    except user.DoesNotExist:
        return redirect('home page')

    if request.method == 'POST':
        owner.name = request.POST.get('full_name', owner.name)
        owner.gender = request.POST.get('gender', owner.gender)
        owner.dob = request.POST.get('dob') or owner.dob
        owner.phone_number = request.POST.get('phone_number', owner.phone_number)
        owner.address = request.POST.get('address', owner.address)
        owner.city = request.POST.get('city', owner.city)
        owner.state = request.POST.get('state', owner.state)
        owner.landmark = request.POST.get('landmark', owner.landmark)

        if 'profile_photo' in request.FILES:
            owner.profile_photo = request.FILES['profile_photo']
        
        owner.save()
        messages.success(request, "Your profile has been updated successfully!")
        return redirect('owner_profile_setup')

    context = {
        'user': owner,
        'user_role': user_role,
    }

    return render(request, 'owner_profile_setup.html', context)

def student_profile_setup(request):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id or user_role != 'student':
        messages.error(request, "You must be logged in as a student to access this page.")
        return redirect('home page')

    try:
        student = user.objects.get(id=user_id)
    except user.DoesNotExist:
        return redirect('home page')

    if request.method == 'POST':
        student.name = request.POST.get('full_name', student.name)
        student.gender = request.POST.get('gender', student.gender)
        student.dob = request.POST.get('dob') or student.dob
        student.phone_number = request.POST.get('phone_number', student.phone_number)
        student.city = request.POST.get('current_city', student.city)
        student.hometown = request.POST.get('hometown', student.hometown)
        student.preferred_room_type = request.POST.get('preferred_room_type', student.preferred_room_type)

        if 'profile_photo' in request.FILES:
            student.profile_photo = request.FILES['profile_photo']
        
        student.save()
        messages.success(request, "Your profile has been updated successfully!")
        return redirect('student_profile_setup')

    context = {
        'user': student,
        'user_role': user_role,
    }
    return render(request, 'student_profile_setup.html', context)

def public_profile(request, user_id):
    # Ensure a user is logged in to view profiles
    if not request.session.get('user_id'):
        messages.error(request, "You must be logged in to view user profiles.")
        return redirect('home page')

    try:
        profile_user = user.objects.get(pk=user_id)
    except user.DoesNotExist:
        messages.error(request, "The user profile you are trying to view does not exist.")
        return redirect('dashboard')

    listings = None
    # If the profile being viewed is an owner, fetch their available listings
    if profile_user.role == 'owner':
        listings = Post.objects.filter(author=profile_user, is_available=True).order_by('-created_at').prefetch_related('images')

    context = {
        'profile_user': profile_user,
        'listings': listings,
        'user_role': request.session.get('user_role') # Pass the viewer's role for the navbar
    }

    return render(request, 'public_profile.html', context)


def profile_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('home page')

    try:
        current_user = user.objects.get(id=user_id)
    except user.DoesNotExist:
        # This case is unlikely if they have a session, but good practice
        request.session.flush()
        return redirect('home page')

    context = {
        'user': current_user,
    }
    return render(request, 'profile.html', context)

def logout(request):
    request.session.flush() # Clear all session data
    return redirect('home page')

def create_post(request):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id:
        return redirect('home page')
    
    if user_role != 'owner':
        messages.error(request, "You must be a Room Owner to create a post.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            current_user = user.objects.get(id=user_id)
            # Double check role on POST
            if current_user.role != 'owner':
                return redirect('dashboard')
        except user.DoesNotExist:
            return redirect('home page')

        # Get data from the form
        title = request.POST.get('title')
        description = request.POST.get('description')
        street_address = request.POST.get('street_address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        contact_number = request.POST.get('contact_number')
        room_type = request.POST.get('room_type')
        area = request.POST.get('area')

        rent = request.POST.get('rent')
        available_from = request.POST.get('available_from')
        amenities = request.POST.getlist('amenities') # Gets a list of selected amenities
        images = request.FILES.getlist('photos') # Gets a list of uploaded image files

        # Create the Post object
        new_post = Post.objects.create(
            author=current_user,
            title=title,
            description=description,
            street_address=street_address,
            city=city,
            state=state,
            postal_code=postal_code,
            contact_number=contact_number,
            room_type=room_type,
            area=area,
            rent=rent,
            available_from=available_from,
            amenities=','.join(amenities) # Store amenities as a comma-separated string
        )

        # Create a PostImage object for each uploaded image
        for image in images:
            PostImage.objects.create(post=new_post, image=image)
        
        messages.success(request, "Your room listing has been created successfully!")
        return redirect('dashboard')

    return render(request, 'create_post.html')

def edit_post(request, post_id):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id or user_role != 'owner':
        messages.error(request, "You must be logged in as an owner to edit a post.")
        return redirect('home page')

    try:
        # Ensure the post exists and belongs to the logged-in owner
        post = Post.objects.get(pk=post_id, author_id=user_id)
    except Post.DoesNotExist:
        messages.error(request, "Listing not found or you do not have permission to edit it.")
        return redirect('dashboard')

    if request.method == 'POST':
        # Update the post object with data from the form
        post.title = request.POST.get('title')
        post.description = request.POST.get('description')
        post.street_address = request.POST.get('street_address')
        post.city = request.POST.get('city')
        post.state = request.POST.get('state')
        post.postal_code = request.POST.get('postal_code')
        post.contact_number = request.POST.get('contact_number')
        post.room_type = request.POST.get('room_type')
        post.area = request.POST.get('area')
        post.rent = request.POST.get('rent')
        post.available_from = request.POST.get('available_from')
        
        amenities = request.POST.getlist('amenities')
        post.amenities = ','.join(amenities)
        
        post.save() # Save the updated fields

        # Handle new image uploads (adds them to existing images)
        images = request.FILES.getlist('photos')
        for image in images:
            PostImage.objects.create(post=post, image=image)
        
        # Handle image deletions
        delete_ids_str = request.POST.get('delete_images', '')
        if delete_ids_str:
            delete_ids = [int(id) for id in delete_ids_str.split(',') if id.isdigit()]
            if delete_ids:
                PostImage.objects.filter(post=post, id__in=delete_ids).delete()

        messages.success(request, "Your listing has been updated successfully!")
        return redirect('dashboard')

    # For a GET request, render the form with existing data
    amenities_list = post.amenities.split(',') if post.amenities else []
    all_amenities = ['wifi', 'kitchen', 'ac', 'laundry', 'parking', 'furnished']

    context = {
        'post': post,
        'amenities_list': amenities_list,
        'all_amenities': all_amenities,
    }
    return render(request, 'edit_post.html', context)

def post_detail(request, post_id):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')

    try:
        post = Post.objects.prefetch_related('images', 'reviews__student').get(pk=post_id)
    except Post.DoesNotExist:
        messages.error(request, "That listing does not exist.")
        return redirect('dashboard')

    # Check if the logged-in user is the author of the post
    is_owner = (user_id == post.author.id)

    # Check if the student has already booked this post
    has_booked = False
    # A student has an "active" booking if it's pending, or if it was accepted and the tenancy is still active.
    if user_role == 'student':
        has_booked = Booking.objects.filter(
            Q(student_id=user_id, post_id=post_id, status='pending') |
            Q(student_id=user_id, post_id=post_id, status='accepted', post__tenancies_history__is_active=True)
        ).exists()

    # Check if the student has saved this post
    is_saved = False
    if user_role == 'student':
        is_saved = SavedPost.objects.filter(student_id=user_id, post_id=post_id).exists()

    # Check if the current student is eligible to leave a review
    can_review = False
    if user_role == 'student':
        # A student can review if they had a tenancy for this post that has ended,
        # and they have not already submitted a review.
        has_ended_tenancy = Tenancy.objects.filter(tenant_id=user_id, post=post, is_active=False).exists()
        has_reviewed = Review.objects.filter(student_id=user_id, post=post).exists()
        can_review = has_ended_tenancy and not has_reviewed

    # Split the amenities string into a list. Handle empty string case.
    amenities_list = post.amenities.split(',') if post.amenities else []

    # Create a full address string for the Google Maps link
    full_address = f"{post.street_address}, {post.city}, {post.state} {post.postal_code}"

    context = {
        'post': post,
        'amenities_list': amenities_list,
        'user_role': user_role,
        'is_owner': is_owner,
        'is_saved': is_saved,
        'can_review': can_review,
        'has_booked': has_booked,
        'full_address': full_address,
    }
    return render(request, 'post_detail.html', context)

def delete_post(request, post_id):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id:
        return redirect('home page')

    # Only owners can delete posts
    if user_role != 'owner':
        messages.error(request, "You must be a Room Owner to delete a post.")
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            # Get the post and make sure the logged-in user is the author
            post_to_delete = Post.objects.get(pk=post_id, author_id=user_id)
            
            # The post object is retrieved, so we can now delete it.
            # Django's CASCADE will also delete related PostImage records.
            # Note: This does not delete the image files from storage.
            post_to_delete.delete()
            
            messages.success(request, "Your listing has been successfully deleted.")
        except Post.DoesNotExist:
            # This happens if the post doesn't exist OR the user is not the author.
            messages.error(request, "You do not have permission to delete this listing or it does not exist.")
        
        return redirect('dashboard')
    
    return redirect('dashboard') # Redirect if not a POST request

def create_booking(request, post_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        messages.error(request, "You must be logged in as a student to book a room.")
        return redirect('post_detail', post_id=post_id)

    try:
        post = Post.objects.get(pk=post_id, is_available=True)
        student = user.objects.get(pk=user_id)
    except (Post.DoesNotExist, user.DoesNotExist):
        messages.error(request, "This listing is not available for booking.")
        return redirect('dashboard')

    # Prevent owner from booking their own post
    if post.author.id == user_id:
        messages.error(request, "You cannot book your own listing.")
        return redirect('post_detail', post_id=post_id)

    # Instead of creating a new booking, get or create one.
    # This handles re-booking after a rejection.
    booking, created = Booking.objects.get_or_create(student=student, post=post)

    if not created:
        # If the booking already existed
        if booking.status == 'pending':
            messages.info(request, "You already have a pending booking request for this room.")
            return redirect('student_bookings')
        elif booking.status == 'accepted':
            # Check if the tenancy for this accepted booking has ended.
            tenancy_ended = not Tenancy.objects.filter(post=post, tenant=student, is_active=True).exists()
            if tenancy_ended:
                # Allow re-booking by resetting the status
                booking.status = 'pending'
                booking.save()
                messages.success(request, f"Your new booking request for '{post.title}' has been sent!")
            else:
                messages.info(request, "You already have an active tenancy for this room.")
        else: # If the status was 'rejected'
            booking.status = 'pending'
            booking.save()
            messages.success(request, f"Your booking request for '{post.title}' has been re-sent to the owner!")
    else:
        # If a new booking was created
        messages.success(request, f"Your booking request for '{post.title}' has been sent to the owner!")
        
        # --- Real-time Notification ---
        channel_layer = get_channel_layer()
        if channel_layer:
            owner_id = post.author.id
            # This is the specific payload for the frontend to understand
            notification_message = {
                'type': 'new_booking_request',
                'payload': {
                    'booking_id': booking.id,
                    'student_name': student.name,
                    'post_title': post.title,
                    'date_sent': booking.created_at.strftime("%B %d, %Y")
                }
            }
            async_to_sync(channel_layer.group_send)(
                f'user_notifications_{owner_id}',
                {
                    'type': 'send_notification', # This calls the method in the consumer
                    'message': notification_message
                }
            )

    return redirect('student_bookings')

def student_bookings(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        return redirect('home page')

    # Only show bookings that are still pending or have been rejected.
    # Accepted bookings (which lead to a tenancy) should no longer appear here.
    bookings = Booking.objects.filter(
        student_id=user_id,
        status__in=['pending', 'rejected']
    ).select_related('post', 'post__author').order_by('-created_at')
    context = {
        'bookings': bookings,
        'user_role': 'student',
    }
    return render(request, 'student_bookings.html', context)

def cancel_booking(request, booking_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        return redirect('home page')

    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('student_bookings')

    try:
        # Ensure the booking belongs to the current user and is still pending
        booking = Booking.objects.get(pk=booking_id, student_id=user_id, status='pending')
        
        # Delete the booking request
        booking.delete()
        
        messages.success(request, "Your booking request has been successfully cancelled.")
    except Booking.DoesNotExist:
        messages.error(request, "Booking request not found or it can no longer be cancelled.")
    
    return redirect('student_bookings')


def student_tenancies(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        return redirect('home page')

    # Get all tenancies for the current student, separated by status
    active_tenancies = Tenancy.objects.filter(
        tenant_id=user_id, is_active=True
    ).select_related('post', 'post__author').order_by('-start_date')

    past_tenancies = Tenancy.objects.filter(
        tenant_id=user_id, is_active=False
    ).select_related('post', 'post__author').order_by('-end_date')

    context = {
        'active_tenancies': active_tenancies,
        'past_tenancies': past_tenancies,
        'active_page': 'tenancies',
        'user_role': 'student',
    }
    return render(request, 'student_tenancies.html', context)

def owner_booking_requests(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'owner':
        return redirect('home page')

    # Get all pending bookings for posts authored by the current owner
    booking_requests = Booking.objects.filter(post__author_id=user_id, status='pending').select_related('student', 'post').order_by('created_at')
    context = {
        'booking_requests': booking_requests,
        'user_role': 'owner'
    }
    return render(request, 'owner_booking_requests.html', context)

def handle_booking_action(request, booking_id, action):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'owner':
        return redirect('home page')

    if request.method != 'POST':
        return redirect('owner_booking_requests')

    try:
        booking = Booking.objects.select_related('post', 'student').get(pk=booking_id, post__author_id=user_id)
    except Booking.DoesNotExist:
        messages.error(request, "Booking request not found or you don't have permission.")
        return redirect('owner_booking_requests')

    if action == 'accept':
        # Set the post as unavailable
        post = booking.post
        post.is_available = False
        post.save()

        # --- Helper function to generate rent payments ---
        def generate_rent_payments(tenancy):
            rent_amount = tenancy.post.rent
            # Generate payments for the next 12 months from the tenancy start date
            for i in range(12):
                due_date = tenancy.start_date + relativedelta(months=i)
                RentPayment.objects.create(tenancy=tenancy, due_date=due_date, amount=rent_amount)

        # Create a tenancy record
        new_tenancy = Tenancy.objects.create(post=post, tenant=booking.student, start_date=datetime.date.today())

        # Update the booking status
        booking.status = 'accepted' 
        booking.save()

        generate_rent_payments(new_tenancy)

        # Reject all other pending bookings for this post
        Booking.objects.filter(post=post, status='pending').update(status='rejected')

        # --- Real-time Notification for Accepted Booking ---
        channel_layer = get_channel_layer()
        if channel_layer:
            student_id = booking.student.id
            notification_message = {
                'type': 'booking_status_update',
                'payload': {
                    'booking_id': booking.id,
                    'status': 'accepted'
                }
            }
            async_to_sync(channel_layer.group_send)(
                f'user_notifications_{student_id}',
                {
                    'type': 'send_notification',
                    'message': notification_message
                }
            )
        messages.success(request, f"You have accepted the booking for '{post.title}' from {booking.student.name}.")
    elif action == 'reject':
        booking.status = 'rejected'
        booking.save()

        # --- Real-time Notification for Rejected Booking ---
        channel_layer = get_channel_layer()
        if channel_layer:
            student_id = booking.student.id
            notification_message = {
                'type': 'booking_status_update',
                'payload': {
                    'booking_id': booking.id,
                    'status': 'rejected'
                }
            }
            async_to_sync(channel_layer.group_send)(
                f'user_notifications_{student_id}',
                {
                    'type': 'send_notification',
                    'message': notification_message
                }
            )
        messages.info(request, f"You have rejected the booking from {booking.student.name}.")

    return redirect('owner_booking_requests')

def assign_tenant(request, post_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('home page')

    try:
        post = Post.objects.get(pk=post_id, author_id=user_id, is_available=True)
    except Post.DoesNotExist:
        messages.error(request, "Listing not found, is already rented, or you don't have permission to edit it.")
        return redirect('dashboard')

    if request.method == 'POST':
        tenant_id = request.POST.get('tenant_id')
        start_date = request.POST.get('start_date')

        if not tenant_id or not start_date:
            messages.error(request, "Please select a tenant and a start date.")
            return redirect('assign_tenant', post_id=post.id)

        try:
            tenant = user.objects.get(pk=tenant_id, role='student')
        except user.DoesNotExist:
            messages.error(request, "Selected student not found.")
            return redirect('assign_tenant', post_id=post.id)

        # --- Helper function to generate rent payments ---
        def generate_rent_payments(tenancy):
            rent_amount = tenancy.post.rent
            # Generate payments for the next 12 months from the tenancy start date
            for i in range(12):
                due_date = tenancy.start_date + relativedelta(months=i)
                RentPayment.objects.create(tenancy=tenancy, due_date=due_date, amount=rent_amount)

        # Create the tenancy record
        new_tenancy = Tenancy.objects.create(post=post, tenant=tenant, start_date=start_date)

        # Mark the post as rented
        post.is_available = False
        post.save()

        generate_rent_payments(new_tenancy)

        messages.success(request, f"{tenant.name} has been assigned to '{post.title}'.")
        return redirect('dashboard')

    # GET request: Show all students to choose from
    students = user.objects.filter(role='student').order_by('name')
    context = {
        'post': post,
        'students': students
    }
    return render(request, 'assign_tenant.html', context)

def tenant_list(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('home page')

    # Get all tenancies for posts authored by the current owner
    tenancies = Tenancy.objects.filter(post__author_id=user_id, is_active=True).select_related('post', 'tenant').order_by('-start_date')

    context = {
        'tenancies': tenancies,
        'user_role': 'owner', # For sidebar navigation
        'active_page': 'my_tenants', # For sidebar highlighting
    }
    return render(request, 'tenant_list.html', context)

def end_tenancy(request, tenancy_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'owner':
        messages.error(request, "You must be logged in as an owner.")
        return redirect('home page')

    # Only allow POST requests for this action
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('tenant_list')

    # At this point, the request is guaranteed to be a POST.
    try:
        tenancy = Tenancy.objects.get(pk=tenancy_id, post__author_id=user_id)
        # Mark tenancy as inactive and set end date
        tenancy.is_active = False
        tenancy.end_date = datetime.date.today()
        tenancy.save()
        # Make the post available again
        tenancy.post.is_available = True
        tenancy.post.save()
        messages.success(request, f"Tenancy for '{tenancy.post.title}' has been ended.")
    except Tenancy.DoesNotExist:
        messages.error(request, "Tenancy not found or you do not have permission.")
    return redirect('tenant_list')

def owner_rent_payments(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'owner':
        messages.error(request, "You must be logged in as an owner.")
        return redirect('home page')
    
    # Get all active tenancies for the owner, along with their associated payments
    from django.db.models import Sum, Case, When, DecimalField
    tenancies = Tenancy.objects.filter(
        post__author_id=user_id, 
        is_active=True
    ).annotate(
        total_paid=Sum(
            Case(
                When(payments__status='paid', then='payments__amount'),
                default=0.0,
                output_field=DecimalField() # Explicitly set the output field for the Case
            )
        ),
        total_due=Sum(
            'payments__amount',
            output_field=DecimalField()
        )
    ).select_related('post', 'tenant').prefetch_related('payments').order_by('-start_date')

    context = {
        'tenancies': tenancies,
        'user_role': 'owner',
        'active_page': 'rent_payments', # For sidebar highlighting
    }
    return render(request, 'owner_rent_payments.html', context)

def mark_payment_paid(request, payment_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'owner':
        messages.error(request, "Unauthorized access.")
        return redirect('home page')

    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('owner_rent_payments')

    try:
        # Ensure the payment belongs to a tenancy owned by the current user
        payment = RentPayment.objects.get(
            pk=payment_id, 
            tenancy__post__author_id=user_id
        )
        
        if payment.status == 'unpaid':
            payment.status = 'paid'
            payment.paid_on = datetime.date.today()
            payment.save()
            messages.success(request, f"Rent for {payment.due_date.strftime('%B %Y')} marked as paid.")
    except RentPayment.DoesNotExist:
        messages.error(request, "Payment record not found.")
    
    return redirect('owner_rent_payments')

def student_rent_payments(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        messages.error(request, "You must be logged in as a student.")
        return redirect('home page')
    
    # Get all active tenancies for the student
    active_tenancies = Tenancy.objects.filter(
        tenant_id=user_id, is_active=True
    ).select_related('post', 'post__author').prefetch_related('payments').order_by('-start_date')

    # For each tenancy, find the next upcoming unpaid payment
    for tenancy in active_tenancies:
        tenancy.next_unpaid_payment = tenancy.payments.filter(status='unpaid').order_by('due_date').first()

    # This logic was causing a TemplateSyntaxError, it's corrected in the template now.
    # try:
    # except Tenancy.DoesNotExist:
    #     active_tenancies = None

    context = {
        'active_tenancies': active_tenancies,
        'user_role': 'student',
        'active_page': 'rent_payments',
    }
    return render(request, 'student_rent_payments.html', context)

def process_payment(request, payment_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        messages.error(request, "Unauthorized access.")
        return redirect('home page')

    try:
        # Security check: Ensure the payment belongs to the logged-in student
        payment = RentPayment.objects.get(pk=payment_id, tenancy__tenant_id=user_id)
    except RentPayment.DoesNotExist:
        messages.error(request, "Payment record not found.")
        return redirect('student_rent_payments')

    if payment.status == 'paid':
        messages.info(request, "This payment has already been made.")
        return redirect('student_rent_payments')

    # This view renders the mock payment page
    return render(request, 'mock_payment_page.html', {'payment': payment})

def confirm_payment(request, payment_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        messages.error(request, "Unauthorized access.")
        return redirect('home page')

    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('student_rent_payments')

    try:
        # Security check: Ensure the payment belongs to the logged-in student
        payment = RentPayment.objects.get(pk=payment_id, tenancy__tenant_id=user_id)
        
        if payment.status == 'unpaid':
            payment.status = 'paid'
            payment.paid_on = datetime.date.today()
            payment.save()

            # --- Real-time Notification for Payment ---
            channel_layer = get_channel_layer()
            if channel_layer:
                owner_id = payment.tenancy.post.author.id
                notification_message = {
                    'type': 'payment_received',
                    'payload': {
                        'payment_id': payment.id,
                        'tenancy_id': payment.tenancy.id,
                        'amount': payment.amount,
                        'student_name': payment.tenancy.tenant.name,
                        'post_title': payment.tenancy.post.title
                    }
                }
                async_to_sync(channel_layer.group_send)(
                    f'user_notifications_{owner_id}',
                    {'type': 'send_notification', 'message': notification_message}
                )

            messages.success(request, f"Payment for {payment.due_date.strftime('%B %Y')} was successful!")
    except RentPayment.DoesNotExist:
        messages.error(request, "Payment record not found.")
    
    return redirect('student_rent_payments')

def report_issue(request, tenancy_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        messages.error(request, "You must be logged in as a student.")
        return redirect('home page')

    try:
        tenancy = Tenancy.objects.get(pk=tenancy_id, tenant_id=user_id, is_active=True)
    except Tenancy.DoesNotExist:
        messages.error(request, "Active tenancy not found.")
        return redirect('student_tenancies')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        image = request.FILES.get('image')

        if not title or not description:
            messages.error(request, "Title and description are required.")
        else:
            new_request = MaintenanceRequest.objects.create(
                tenancy=tenancy,
                title=title,
                description=description,
                priority=priority,
                image=image
            )

            # --- Real-time Notification for Maintenance Request ---
            channel_layer = get_channel_layer()
            if channel_layer:
                owner_id = tenancy.post.author.id
                notification_message = {
                    'type': 'new_maintenance_request',
                    'payload': {
                        'request_id': new_request.id,
                        'title': new_request.title,
                        'priority': new_request.priority,
                        'student_name': tenancy.tenant.name,
                        'post_title': tenancy.post.title
                    }
                }
                async_to_sync(channel_layer.group_send)(
                    f'user_notifications_{owner_id}',
                    {'type': 'send_notification', 'message': notification_message}
                )

            messages.success(request, "Your maintenance request has been submitted successfully.")
            return redirect('student_tenancies')

    return render(request, 'report_issue.html', {'tenancy': tenancy})

def owner_maintenance_list(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'owner':
        messages.error(request, "You must be logged in as an owner.")
        return redirect('home page')

    all_requests = MaintenanceRequest.objects.filter(
        tenancy__post__author_id=user_id
    ).select_related('tenancy__post', 'tenancy__tenant').order_by('-created_at')

    open_requests = all_requests.exclude(status='completed')
    closed_requests = all_requests.filter(status='completed')

    context = {
        'open_requests': open_requests,
        'closed_requests': closed_requests,
        'open_requests_count': open_requests.count(),
        'closed_requests_count': closed_requests.count(),
        'user_role': 'owner',
        'active_page': 'maintenance'
    }
    return render(request, 'owner_maintenance_list.html', context)

def maintenance_request_detail(request, request_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('home page')

    try:
        maintenance_request = MaintenanceRequest.objects.select_related(
            'tenancy__post', 'tenancy__tenant', 'tenancy__post__author'
        ).prefetch_related('comments__author').get(pk=request_id)
    except MaintenanceRequest.DoesNotExist:
        messages.error(request, "Maintenance request not found.")
        return redirect('dashboard')

    # Security check: ensure the user is either the tenant or the owner
    is_owner = maintenance_request.tenancy.post.author_id == user_id
    is_tenant = maintenance_request.tenancy.tenant_id == user_id

    if not is_owner and not is_tenant:
        messages.error(request, "You do not have permission to view this request.")
        return redirect('dashboard')

    if request.method == 'POST':
        # Handle status update by owner
        if is_owner and 'new_status' in request.POST:
            new_status = request.POST.get('new_status')
            if new_status in [choice[0] for choice in MaintenanceRequest.STATUS_CHOICES]:
                maintenance_request.status = new_status
                maintenance_request.save()
                messages.success(request, f"Request status updated to '{maintenance_request.get_status_display()}'.")
                return redirect('maintenance_request_detail', request_id=request_id)

        # Handle comment submission by either owner or tenant
        if 'comment_text' in request.POST:
            comment_text = request.POST.get('comment_text')
            if comment_text:
                MaintenanceComment.objects.create(
                    request=maintenance_request,
                    author_id=user_id,
                    text=comment_text
                )
                messages.success(request, "Your comment has been added.")
                return redirect('maintenance_request_detail', request_id=request_id)

    context = {
        'request': maintenance_request,
        'user_role': request.session.get('user_role'),
        'is_owner': is_owner
    }
    return render(request, 'maintenance_request_detail.html', context)

def register_student(request):
    if request.method == 'POST':
        na = request.POST['full_name']
        email = request.POST['email']
        password = request.POST['password1']
        password2 = request.POST['password2']
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        dob_str = request.POST.get('dob')

        # Basic validation
        if not all([na, email, password, age, gender, dob_str]):
            messages.error(request, "All fields are required for student registration.")
            return redirect('home page')

        # --- Add password confirmation ---
        if password != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('home page')

        if user.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('home page')

        try:
            age = int(age)
            dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid age or date of birth format.")
            return redirect('home page')

        hashed_password = make_password(password)
        obj = user(
            name=na,
            email=email,
            password=hashed_password,
            role='student',
            age=age,
            gender=gender, # This was the line with the syntax error
            dob=dob,
        )
        obj.save()
        
        messages.success(request, "Student account created successfully! Please log in.")
        return redirect(f"{reverse('home page')}?from=student")
    return redirect('home page') # Redirect GET requests or failed POSTs

def toggle_save_post(request, post_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        saved_post, created = SavedPost.objects.get_or_create(student_id=user_id, post_id=post_id)
        if not created:
            saved_post.delete()
            return JsonResponse({'status': 'unsaved'})
        else:
            return JsonResponse({'status': 'saved'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def saved_posts_list(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        return redirect('home page')

    saved_posts = Post.objects.filter(saved_by__student_id=user_id).order_by('-saved_by__created_at').prefetch_related('images')
    
    context = {
        'posts': saved_posts,
        'user_role': 'student',
    }
    return render(request, 'saved_posts.html', context)

def add_review(request, post_id):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('user_role') != 'student':
        messages.error(request, "You must be logged in as a student to leave a review.")
        return redirect('post_detail', post_id=post_id)

    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return redirect('dashboard')

    # Check eligibility again on the backend
    has_ended_tenancy = Tenancy.objects.filter(tenant_id=user_id, post=post, is_active=False).exists()
    has_reviewed = Review.objects.filter(student_id=user_id, post=post).exists()
    is_eligible = has_ended_tenancy and not has_reviewed

    if not is_eligible:
        messages.error(request, "You are not eligible to review this listing.")
        return redirect('post_detail', post_id=post_id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating or not comment:
            messages.error(request, "Both rating and comment are required.")
            return render(request, 'add_review.html', {'post': post})

        Review.objects.create(
            post=post,
            student_id=user_id,
            rating=int(rating),
            comment=comment
        )

        # Recalculate and update the average rating for the post
        new_avg = post.reviews.aggregate(Avg('rating'))['rating__avg']
        post.average_rating = new_avg if new_avg is not None else 0
        post.save()

        messages.success(request, "Your review has been submitted successfully!")
        return redirect('post_detail', post_id=post_id)

    return render(request, 'add_review.html', {'post': post})

def start_conversation(request, post_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "You must be logged in to start a conversation.")
        return redirect('post_detail', post_id=post_id)

    try:
        post = Post.objects.get(pk=post_id)
        current_user = user.objects.get(pk=user_id)
    except (Post.DoesNotExist, user.DoesNotExist):
        messages.error(request, "Post or user not found.")
        return redirect('dashboard')

    # Prevent owner from messaging themselves
    if post.author.id == user_id:
        messages.error(request, "You cannot start a conversation about your own listing.")
        return redirect('post_detail', post_id=post_id)

    # Find if a conversation already exists between these two users for this post
    conversation = Conversation.objects.filter(
        post=post,
        participants=current_user
    ).filter(
        participants=post.author
    ).first()

    # If no conversation exists, create one
    if not conversation:
        conversation = Conversation.objects.create(post=post)
        conversation.participants.add(current_user, post.author)

    return redirect('conversation_detail', conversation_id=conversation.id)

def inbox(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('home page')

    try:
        current_user = user.objects.get(pk=user_id)
    except user.DoesNotExist:
        return redirect('home page')

    conversations = Conversation.objects.filter(participants=current_user).prefetch_related('participants', 'post', 'messages')

    # Add the other participant to each conversation object for easy access in the template
    for conv in conversations:
        conv.other_participant = conv.participants.exclude(id=user_id).first()
        # Check for unread messages in this specific conversation for the current user
        conv.has_unread = conv.messages.exclude(sender=current_user).exclude(read_by=current_user).exists()

    context = {
        'conversations': conversations,
        # Pass user_id for template logic if needed, though request.session.user_id is also available
        'user_id': user_id,
        'user_role': request.session.get('user_role'),
    }
    return render(request, 'inbox.html', context)

def conversation_detail(request, conversation_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('home page')

    # Get the current user object, which is needed for marking messages as read.
    try:
        current_user = user.objects.get(pk=user_id)
    except user.DoesNotExist:
        request.session.flush() # Clear session if user ID is invalid
        messages.error(request, "User not found. Please log in again.")
        return redirect('home page')

    try:
        # Ensure the user is a participant of the conversation
        conversation = Conversation.objects.prefetch_related('messages__sender', 'participants').get(pk=conversation_id, participants__id=user_id)
    except Conversation.DoesNotExist:
        messages.error(request, "Conversation not found or you are not a participant.")
        return redirect('inbox')

    # Mark messages as read
    # Find messages in this conversation not sent by the user and add the user to the 'read_by' list.
    messages_to_mark_as_read = conversation.messages.exclude(sender_id=user_id)
    for message in messages_to_mark_as_read:
        message.read_by.add(current_user)

    if request.method == 'POST':
        text = request.POST.get('message_text')
        if text:
            new_message = Message.objects.create(
                conversation=conversation,
                sender_id=user_id,
                text=text
            )
            # The sender has implicitly "read" their own message
            new_message.read_by.add(current_user)

            # --- Real-time Notification for New Message ---
            other_participant = conversation.participants.exclude(id=user_id).first()
            channel_layer = get_channel_layer()
            if channel_layer and other_participant:
                # 1. Send a global notification to the recipient's notification bell
                async_to_sync(channel_layer.group_send)(
                    f'user_notifications_{other_participant.id}',
                    {
                        'type': 'send_notification',
                        'message': {
                            'type': 'new_message',
                            'message': f'You have a new message from {current_user.name} regarding "{conversation.post.title}".'
                        }
                    }
                )

                # 2. Send the message content to the conversation-specific chat group
                async_to_sync(channel_layer.group_send)(
                    f'chat_{conversation_id}',
                    {
                        'type': 'new_message',
                        'text': new_message.text,
                        'sender_id': user_id,
                    }
                )
            conversation.save() # This will update the `updated_at` timestamp
            return redirect('conversation_detail', conversation_id=conversation.id)

    other_participant = conversation.participants.exclude(id=user_id).first()

    context = {
        'conversation': conversation,
        'other_participant': other_participant,
        'user_role': request.session.get('user_role'),
    }
    return render(request, 'conversation_detail.html', context)

def get_unread_notifications(request):
    """
    API endpoint to fetch unread conversation data for the notification bell.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        current_user = user.objects.get(pk=user_id)
    except user.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    # Find conversations that have messages not sent by the current user AND not read by the current user.
    unread_conversations = Conversation.objects.filter(
        participants=current_user
    ).annotate(
        has_unread_messages=Exists(
            Message.objects.filter(
                conversation=OuterRef('pk')
        ).exclude(Q(sender=current_user) | Q(read_by=current_user))
        )
    ).filter(has_unread_messages=True)

    unread_count = unread_conversations.count()

    # Prepare data for the dropdown (limited to 5 for brevity)
    conversations_data = []
    for conv in unread_conversations[:5]:
        other_participant = conv.participants.exclude(id=user_id).first()
        conversations_data.append({
            'id': conv.id,
            'participant_name': other_participant.name if other_participant else 'A user',
            'post_title': conv.post.title,
        })

    return JsonResponse({'unread_count': unread_count, 'conversations': conversations_data})
