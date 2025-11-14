import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextType {
  apiKey: string | null;
  usuarioId: number | null;
  isAuthenticated: boolean;
  login: (correo: string, contrasena: string) => Promise<void>;
  register: (correo: string, contrasena: string, nombre?: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = 'http://127.0.0.1:5000';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [usuarioId, setUsuarioId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Recuperar sesión almacenada
    const storedApiKey = localStorage.getItem('api_key');
    const storedUsuarioId = localStorage.getItem('usuario_id');
    
    if (storedApiKey && storedUsuarioId) {
      setApiKey(storedApiKey);
      setUsuarioId(parseInt(storedUsuarioId));
    }
    setIsLoading(false);
  }, []);

  const login = async (correo: string, contrasena: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ correo, contrasena }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Credenciales inválidas');
        }
        throw new Error('Error al iniciar sesión');
      }

      const data = await response.json();
      
      // Guardar en estado y localStorage
      setApiKey(data.api_key);
      setUsuarioId(data.usuario_id);
      localStorage.setItem('api_key', data.api_key);
      localStorage.setItem('usuario_id', data.usuario_id.toString());
    } catch (error) {
      console.error('Error en login:', error);
      throw error;
    }
  };

  const register = async (correo: string, contrasena: string, nombre?: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ correo, contrasena, nombre }),
      });

      if (!response.ok) {
        if (response.status === 409) {
          throw new Error('El correo ya está registrado');
        }
        throw new Error('Error al registrarse');
      }

      const data = await response.json();
      
      // Guardar en estado y localStorage
      setApiKey(data.api_key);
      setUsuarioId(data.usuario_id);
      localStorage.setItem('api_key', data.api_key);
      localStorage.setItem('usuario_id', data.usuario_id.toString());
    } catch (error) {
      console.error('Error en registro:', error);
      throw error;
    }
  };

  const logout = () => {
    setApiKey(null);
    setUsuarioId(null);
    localStorage.removeItem('api_key');
    localStorage.removeItem('usuario_id');
  };

  return (
    <AuthContext.Provider
      value={{
        apiKey,
        usuarioId,
        isAuthenticated: !!apiKey,
        login,
        register,
        logout,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
