"""Frontend code templates - Part 1"""


class FrontendTemplates:
    """Provides fallback templates for frontend code generation"""
    
    def get_index_html_template(self) -> str:
        return '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Auto-Generated App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>'''
    
    def get_main_template(self) -> str:
        return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)'''
    
    def get_app_template(self) -> str:
        return '''import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Home from './pages/Home'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App'''
    
    def get_router_template(self) -> str:
        return "// Router template"
    
    def get_api_client_template(self) -> str:
        return '''import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
})

export { api }'''
    
    def get_auth_context_template(self) -> str:
        return '''import { createContext, useContext, useState } from 'react'

interface AuthContextType {
  user: any
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)

  const login = async (username: string, password: string) => {}
  const register = async (email: string, username: string, password: string) => {}
  const logout = () => setUser(null)

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)!
}'''
    
    def get_page_template(self, page_name: str) -> str:
        return f"export default function {page_name}() {{ return <div>{page_name}</div> }}"
    
    def get_component_template(self, component_name: str) -> str:
        return f"export default function {component_name}() {{ return <div>{component_name}</div> }}"
    
    def get_types_template(self) -> str:
        return "export interface User { id: number; username: string; email: string }"
    
    def get_utils_template(self) -> str:
        return "export const formatDate = (date: Date) => date.toISOString()"
    
    def get_styles_template(self) -> str:
        return '''@tailwind base;
@tailwind components;
@tailwind utilities;'''
    
    def get_config_template(self) -> str:
        return "export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'"
    
    def get_package_json_template(self) -> str:
        return '''{
  "name": "frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}'''
    
    def get_vite_config_template(self) -> str:
        return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
  },
})'''
    
    def get_tailwind_config_template(self) -> str:
        return '''module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}'''
    
    def get_tsconfig_template(self) -> str:
        return '''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}'''
