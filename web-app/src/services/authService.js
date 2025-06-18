import { apiService } from './apiService'

class AuthService {
  async login(email, password) {
    try {
      const response = await apiService.post('/auth/login', {
        email,
        password
      })
      
      return response
    } catch (error) {
      throw new Error(error.message || 'Login failed')
    }
  }

  async register(userData) {
    try {
      const response = await apiService.post('/auth/register', userData)
      return response
    } catch (error) {
      throw new Error(error.message || 'Registration failed')
    }
  }

  async logout() {
    try {
      await apiService.post('/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  async validateToken(token) {
    try {
      const response = await apiService.get('/auth/validate', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      return response
    } catch (error) {
      throw new Error('Token validation failed')
    }
  }

  async updateProfile(profileData) {
    try {
      const response = await apiService.put('/auth/profile', profileData)
      return response.user
    } catch (error) {
      throw new Error(error.message || 'Profile update failed')
    }
  }

  async changePassword(currentPassword, newPassword) {
    try {
      const response = await apiService.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
      return response
    } catch (error) {
      throw new Error(error.message || 'Password change failed')
    }
  }

  async requestPasswordReset(email) {
    try {
      const response = await apiService.post('/auth/forgot-password', { email })
      return response
    } catch (error) {
      throw new Error(error.message || 'Password reset request failed')
    }
  }

  async resetPassword(token, newPassword) {
    try {
      const response = await apiService.post('/auth/reset-password', {
        token,
        new_password: newPassword
      })
      return response
    } catch (error) {
      throw new Error(error.message || 'Password reset failed')
    }
  }

  async enable2FA() {
    try {
      const response = await apiService.post('/auth/2fa/enable')
      return response
    } catch (error) {
      throw new Error(error.message || '2FA setup failed')
    }
  }

  async verify2FA(code) {
    try {
      const response = await apiService.post('/auth/2fa/verify', { code })
      return response
    } catch (error) {
      throw new Error(error.message || '2FA verification failed')
    }
  }

  async disable2FA(code) {
    try {
      const response = await apiService.post('/auth/2fa/disable', { code })
      return response
    } catch (error) {
      throw new Error(error.message || '2FA disable failed')
    }
  }
}

export const authService = new AuthService()

