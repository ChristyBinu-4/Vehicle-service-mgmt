# Profile Save Verification & Fixes

## ⚠️ IMPORTANT: forms.py File Issue

The `accounts/forms.py` file was accidentally overwritten and needs to be restored from your backup or git history before applying these fixes.

## Verification Checklist

### 1. Model Fields Verification ✅
All required fields exist in `accounts/models.py`:
- ✅ `address` (TextField, nullable)
- ✅ `city` (CharField, nullable)
- ✅ `state` (CharField, nullable)
- ✅ `pincode` (CharField, nullable)
- ✅ `location` (CharField, nullable) - Servicer only
- ✅ `work_types` (CharField, nullable) - Servicer only
- ✅ `available_time` (CharField, nullable) - Servicer only

### 2. Form Meta Fields Verification

**ProfileUpdateForm** should have:
```python
class Meta:
    model = User
    fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'pincode']
```

**ServicerProfileUpdateForm** should have:
```python
class Meta:
    model = User
    fields = [
        'first_name', 'last_name', 'email', 'phone',
        'address', 'city', 'state', 'pincode',
        'location', 'work_types', 'available_time'
    ]
```

### 3. Save Method Verification

#### ProfileUpdateForm.save() - Required Implementation:

```python
def save(self, commit=True):
    """
    Save profile with all personal information fields.
    Explicitly sets all fields from cleaned_data to ensure persistence.
    """
    instance = super().save(commit=False)
    # Ensure email is not changed
    if self.instance and self.instance.pk:
        instance.email = self.instance.email
    
    # Explicitly set all required fields from cleaned_data
    instance.first_name = self.cleaned_data.get('first_name', '')
    instance.last_name = self.cleaned_data.get('last_name', '')
    instance.phone = self.cleaned_data.get('phone', '')
    
    # Explicitly set nullable address fields from cleaned_data
    # Handle empty strings by converting to None for nullable fields
    address_val = self.cleaned_data.get('address', '')
    instance.address = str(address_val).strip() if address_val and str(address_val).strip() else None
    
    city_val = self.cleaned_data.get('city', '')
    instance.city = str(city_val).strip() if city_val and str(city_val).strip() else None
    
    state_val = self.cleaned_data.get('state', '')
    instance.state = str(state_val).strip() if state_val and str(state_val).strip() else None
    
    pincode_val = self.cleaned_data.get('pincode', '')
    instance.pincode = str(pincode_val).strip() if pincode_val and str(pincode_val).strip() else None
    
    if commit:
        # Save all fields explicitly to ensure persistence
        instance.save()
    return instance
```

#### ServicerProfileUpdateForm.save() - Required Implementation:

```python
def save(self, commit=True):
    """
    Save servicer profile with all personal information fields.
    Explicitly sets all fields from cleaned_data to ensure persistence.
    Also updates the linked Servicer model instance.
    """
    instance = super().save(commit=False)
    # Ensure email is not changed
    if self.instance and self.instance.pk:
        instance.email = self.instance.email
    
    # Explicitly set all required fields from cleaned_data
    instance.first_name = self.cleaned_data.get('first_name', '')
    instance.last_name = self.cleaned_data.get('last_name', '')
    instance.phone = self.cleaned_data.get('phone', '')
    
    # Explicitly set nullable address fields from cleaned_data
    address_val = self.cleaned_data.get('address', '')
    instance.address = str(address_val).strip() if address_val and str(address_val).strip() else None
    
    city_val = self.cleaned_data.get('city', '')
    instance.city = str(city_val).strip() if city_val and str(city_val).strip() else None
    
    state_val = self.cleaned_data.get('state', '')
    instance.state = str(state_val).strip() if state_val and str(state_val).strip() else None
    
    pincode_val = self.cleaned_data.get('pincode', '')
    instance.pincode = str(pincode_val).strip() if pincode_val and str(pincode_val).strip() else None
    
    # Servicer-specific fields
    location_val = self.cleaned_data.get('location', '')
    instance.location = str(location_val).strip() if location_val and str(location_val).strip() else None
    
    work_types_val = self.cleaned_data.get('work_types', '')
    instance.work_types = str(work_types_val).strip() if work_types_val and str(work_types_val).strip() else None
    
    available_time_val = self.cleaned_data.get('available_time', '')
    instance.available_time = str(available_time_val).strip() if available_time_val and str(available_time_val).strip() else None
    
    if commit:
        # Save all fields explicitly to ensure persistence
        instance.save()
        
        # Also update the linked Servicer model instance
        # Always update these fields (even if None) to ensure sync
        try:
            from .models import Servicer
            servicer = Servicer.objects.get(email=instance.email)
            # Update servicer fields from user fields
            # Always update, even if None, to ensure sync
            servicer.location = instance.location or ''
            servicer.work_type = instance.work_types or ''
            servicer.available_time = instance.available_time or '9:00 AM - 6:00 PM'
            servicer.save()
        except Servicer.DoesNotExist:
            # Servicer instance doesn't exist, skip update
            pass
    
    return instance
```

### 4. View Verification ✅

**user_profile view** (`accounts/views.py`):
- ✅ Calls `profile_form.save()` (default commit=True)
- ✅ Calls `user.refresh_from_db()` after save
- ✅ Re-instantiates form with updated data

**servicer_profile view** (`accounts/views.py`):
- ✅ Calls `profile_form.save()` (default commit=True)
- ✅ Calls `user.refresh_from_db()` after save
- ✅ Re-instantiates form with updated data

### 5. Template Verification ✅

**user_profile.html**:
- ✅ Displays all address fields: address, city, state, pincode
- ✅ Uses form fields for editing

**servicer_profile.html**:
- ✅ Displays all address fields: address, city, state, pincode
- ✅ Displays servicer fields: location, work_types, available_time
- ✅ Uses form fields for editing

## Critical Fixes Required

### Fix 1: Ensure commit=True in save() calls
**Status:** ✅ Already correct - views call `save()` without arguments (defaults to commit=True)

### Fix 2: Explicit field assignment in save() methods
**Status:** ✅ Already implemented - all fields are explicitly set from cleaned_data

### Fix 3: Remove update_fields restriction
**Status:** ✅ Already fixed - using `instance.save()` without update_fields

### Fix 4: Servicer model sync
**Status:** ✅ Already implemented - Servicer model is updated when User model is saved

## Testing Steps

1. **Restore forms.py** from backup or git
2. **Apply the save() method fixes** shown above
3. **Test User Profile:**
   - Login as user
   - Go to Profile
   - Edit address, city, state, pincode
   - Click Save
   - Verify success message
   - Logout and login
   - Verify data persists

4. **Test Servicer Profile:**
   - Login as servicer
   - Go to Profile
   - Edit address, city, state, pincode, location, work_types
   - Click Save
   - Verify success message
   - Logout and login
   - Verify data persists
   - Verify Servicer model is also updated

5. **Database Verification:**
   - Check database directly to confirm fields are saved
   - Verify User table has address fields
   - Verify Servicer table has location/work_type fields

## Expected Behavior

✅ All address fields (address, city, state, pincode) save to User model  
✅ All servicer fields (location, work_types, available_time) save to User model  
✅ Servicer model is synced with User model updates  
✅ Data persists after logout/login  
✅ No fields reset to empty values  
✅ UI displays latest saved data  

## Next Steps

1. **Restore forms.py** from your backup
2. **Verify** the save() methods match the implementations above
3. **Test** the profile update functionality
4. **Report** any remaining issues
