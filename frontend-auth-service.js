// frontend-auth-service.js
// This is a sample implementation for the frontend to use the new test-refresh-token endpoint

import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Create axios instances
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important: This enables sending cookies with requests
});

// Auth-specific API instance
const authApi = {
  register: (email, password, fullName) =>
    api.post('/auth/register', { email, password, full_name: fullName }),

  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  // Updated to use the new test-refresh-token endpoint
  // This doesn't need to send the refresh token in the body since it's in the cookie
  refreshToken: () =>
    api.post('/auth/test-refresh-token'),

  logout: () =>
    api.post('/auth/logout'),

  getCurrentUser: () =>
    api.get('/auth/me'),

  updateProfile: (fullName, email) =>
    api.put('/auth/update-profile', { full_name: fullName, email }),

  changePassword: (currentPassword, newPassword) =>
    api.put('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
};

// Add request interceptor to include auth token in headers
api.interceptors.request.use(
  (config) => {
    // Get token from localStorage if you're storing it there
    // Note: With HTTP-only cookies, you don't need to manually add the token
    // But some APIs might still expect it in the Authorization header
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for handling token expiration
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If the error is 401 Unauthorized and we haven't already tried to refresh the token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Call the new test-refresh-token endpoint
        const refreshResponse = await authApi.refreshToken();

        // If token refresh was successful
        if (refreshResponse.data.access_token) {
          // Store the new access token if needed
          localStorage.setItem('token', refreshResponse.data.access_token);

          // Update the authorization header for the original request
          originalRequest.headers.Authorization = `Bearer ${refreshResponse.data.access_token}`;

          // Retry the original request with the new token
          return axios(originalRequest);
        }
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        
        // If refresh token is invalid or expired, redirect to login
        redirectToLogin();
        return Promise.reject(refreshError);
      }
    }

    // If the error is not 401 or token refresh failed, reject the promise
    return Promise.reject(error);
  }
);

// Helper function to redirect to login page
const redirectToLogin = () => {
  // Clear any stored tokens
  localStorage.removeItem('token');
  
  // Redirect to login page
  window.location.href = '/login';
};

// Auth state management
const AuthService = {
  isAuthenticated: () => {
    // Check if user is authenticated
    // This could be based on token existence or expiry
    return !!localStorage.getItem('token');
  },

  getToken: () => {
    return localStorage.getItem('token');
  },

  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  },

  login: async (email, password) => {
    try {
      const response = await authApi.login(email, password);
      
      // Store the access token
      if (response.data.access_token) {
        AuthService.setToken(response.data.access_token);
      }
      
      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear token regardless of API success
      AuthService.setToken(null);
    }
  },

  refreshToken: async () => {
    try {
      const response = await authApi.refreshToken();
      
      if (response.data.access_token) {
        AuthService.setToken(response.data.access_token);
      }
      
      return response.data;
    } catch (error) {
      console.error('Token refresh error:', error);
      AuthService.setToken(null);
      throw error;
    }
  }
};

export { api, authApi, AuthService };
