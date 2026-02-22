# Session Timeout System

## Overview
The PortAct application now includes an intelligent inactivity-based session timeout system that automatically logs out users after a period of inactivity, with advance warnings to prevent data loss.

## Features

### 1. **Inactivity-Based Timeout**
- Session timeout is based on user inactivity, not a fixed time from login
- Any user interaction resets the timer
- Tracked activities include:
  - Mouse movements
  - Mouse clicks
  - Keyboard input
  - Scrolling
  - Touch events
  - API calls

### 2. **Advance Warning System**
- Users receive a warning dialog 2 minutes before automatic logout
- Warning includes:
  - Countdown timer showing remaining time
  - Visual progress bar
  - Options to stay logged in or logout immediately
  - Cannot be dismissed by clicking outside or pressing ESC

### 3. **Configurable Timeouts**
Current configuration (can be adjusted in `frontend/src/components/SessionTimeout.tsx`):
- **Inactivity Timeout**: 30 minutes
- **Warning Time**: 2 minutes before timeout
- **Countdown Update**: Every 1 second

### 4. **Smart Activity Tracking**
- Throttled activity detection (1-second intervals) to prevent excessive timer resets
- API calls automatically tracked via Axios interceptors
- Last activity timestamp stored in localStorage

### 5. **User-Friendly Messages**
- Clear warning messages in the dialog
- Session expiration message on login page
- Different messages for manual logout vs. automatic timeout

## Technical Implementation

### Components

#### 1. **SessionTimeout Component** (`frontend/src/components/SessionTimeout.tsx`)
Main component that handles:
- Activity event listeners
- Timer management
- Warning dialog display
- Automatic logout

Key configuration constants:
```typescript
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes
const WARNING_TIME = 2 * 60 * 1000; // 2 minutes warning
const COUNTDOWN_INTERVAL = 1000; // 1 second updates
```

#### 2. **API Interceptor** (`frontend/src/services/api.ts`)
Enhanced to:
- Track API activity timestamps
- Handle 401 errors gracefully
- Redirect to login with appropriate messages

#### 3. **Login Page** (`frontend/src/pages/Login.tsx`)
Updated to:
- Display session timeout messages
- Handle query parameters for session expiration
- Show warning alerts for expired sessions

### Integration

The SessionTimeout component is integrated at the app level in `App.tsx`:
```typescript
<SessionTimeout />
```

This ensures it's active across all protected routes.

## User Experience Flow

### Normal Activity
1. User logs in
2. Timer starts (30 minutes)
3. User interacts with the application
4. Timer resets on each interaction
5. User continues working without interruption

### Approaching Timeout
1. User becomes inactive for 28 minutes
2. Warning dialog appears with 2-minute countdown
3. User has two options:
   - Click "Stay Logged In" → Timer resets, session continues
   - Click "Logout" → Immediate logout
4. If no action taken, automatic logout occurs at 30 minutes

### After Timeout
1. User is redirected to login page
2. Warning message displayed: "Your session has expired due to inactivity."
3. User can log in again to continue

### Backend Token Expiration
1. If backend token expires (401 error)
2. User is redirected to login page
3. Message displayed: "Your session has expired. Please log in again."

## Configuration

### Adjusting Timeout Duration

To change the inactivity timeout period, edit `frontend/src/components/SessionTimeout.tsx`:

```typescript
// Change from 30 minutes to desired duration
const INACTIVITY_TIMEOUT = 45 * 60 * 1000; // 45 minutes
```

### Adjusting Warning Time

To change when the warning appears:

```typescript
// Change from 2 minutes to desired duration
const WARNING_TIME = 5 * 60 * 1000; // 5 minutes warning
```

### Disabling Session Timeout

To disable the session timeout feature, remove or comment out the component in `App.tsx`:

```typescript
// <SessionTimeout />
```

## Security Considerations

1. **Token Storage**: JWT tokens are stored in localStorage
2. **Activity Tracking**: Last activity timestamp tracked for session management
3. **Automatic Cleanup**: All auth data cleared on logout/timeout
4. **Backend Validation**: Backend still validates token expiration independently

## Testing

### Manual Testing Steps

1. **Test Inactivity Timeout**:
   - Log in to the application
   - Wait 28 minutes without any interaction
   - Verify warning dialog appears
   - Verify countdown timer works
   - Wait for automatic logout

2. **Test Activity Reset**:
   - Log in to the application
   - Perform various activities (click, type, scroll)
   - Verify no warning appears during active use

3. **Test "Stay Logged In"**:
   - Trigger the warning dialog
   - Click "Stay Logged In"
   - Verify dialog closes and timer resets

4. **Test Manual Logout**:
   - Trigger the warning dialog
   - Click "Logout"
   - Verify immediate logout and redirect

5. **Test Backend Token Expiration**:
   - Manually expire the backend token
   - Make an API call
   - Verify 401 handling and redirect

### Automated Testing

For automated testing, you can adjust the timeout values to shorter durations:

```typescript
// Test configuration
const INACTIVITY_TIMEOUT = 2 * 60 * 1000; // 2 minutes for testing
const WARNING_TIME = 30 * 1000; // 30 seconds warning
```

## Troubleshooting

### Warning Dialog Not Appearing
- Check browser console for errors
- Verify SessionTimeout component is mounted
- Check if user is authenticated

### Timer Not Resetting
- Verify event listeners are attached
- Check browser console for errors
- Ensure activity throttling is working

### Immediate Logout
- Check backend token expiration settings
- Verify API interceptor is working
- Check for 401 errors in network tab

## Future Enhancements

Potential improvements:
1. Configurable timeout via user preferences
2. Different timeout durations for different user roles
3. Remember user's "Stay Logged In" preference
4. Activity heatmap for security monitoring
5. Multiple device session management
6. Graceful handling of unsaved changes

## Related Files

- `frontend/src/components/SessionTimeout.tsx` - Main component
- `frontend/src/App.tsx` - Integration point
- `frontend/src/services/api.ts` - API interceptor
- `frontend/src/pages/Login.tsx` - Login page with messages
- `frontend/src/store/slices/authSlice.ts` - Auth state management
- `backend/app/core/config.py` - Backend token expiration settings
- `backend/app/core/security.py` - JWT token creation

## Made with Bob