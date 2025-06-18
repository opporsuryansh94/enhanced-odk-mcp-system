import { createContext, useContext, useState, useEffect } from 'react'
import { authService } from '../services/authService'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [organization, setOrganization] = useState(null)

  useEffect(() => {
    // Check for existing session on app load
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token')
        if (token) {
          const userData = await authService.validateToken(token)
          setUser(userData.user)
          setOrganization(userData.organization)
        }
      } catch (error) {
        console.error('Auth initialization failed:', error)
        localStorage.removeItem('auth_token')
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [])

  const login = async (email, password) => {
    try {
      setLoading(true)
      const response = await authService.login(email, password)
      
      setUser(response.user)
      setOrganization(response.organization)
      localStorage.setItem('auth_token', response.token)
      
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.message || 'Login failed' 
      }
    } finally {
      setLoading(false)
    }
  }

  const register = async (userData) => {
    try {
      setLoading(true)
      const response = await authService.register(userData)
      
      setUser(response.user)
      setOrganization(response.organization)
      localStorage.setItem('auth_token', response.token)
      
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.message || 'Registration failed' 
      }
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    try {
      await authService.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setUser(null)
      setOrganization(null)
      localStorage.removeItem('auth_token')
    }
  }

  const updateProfile = async (profileData) => {
    try {
      const updatedUser = await authService.updateProfile(profileData)
      setUser(updatedUser)
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.message || 'Profile update failed' 
      }
    }
  }

  const value = {
    user,
    organization,
    loading,
    login,
    register,
    logout,
    updateProfile,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin'
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

