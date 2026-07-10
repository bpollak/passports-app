import { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from 'react'

export type Language = 'en' | 'es' | 'zh' | 'vi'
export type LocationId = 'csc' | 'bookstore'

interface AuthState {
  token: string
  locationId: LocationId
}

interface AppState {
  currentLanguage: Language
  kioskLocation: LocationId | null
  auth: AuthState | null
}

interface AppContextValue extends AppState {
  setLanguage: (lang: Language) => void
  setKioskLocation: (loc: LocationId | null) => void
  login: (token: string, locationId: LocationId) => void
  logout: () => void
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>({
    currentLanguage: 'en',
    kioskLocation: null,
    auth: null,
  })

  const setLanguage = useCallback((lang: Language) => setState(s => ({ ...s, currentLanguage: lang })), [])
  const setKioskLocation = useCallback((loc: LocationId | null) => setState(s => ({ ...s, kioskLocation: loc })), [])
  const login = useCallback((token: string, locationId: LocationId) => setState(s => ({ ...s, auth: { token, locationId } })), [])
  const logout = useCallback(() => setState(s => ({ ...s, auth: null })), [])

  const value = useMemo<AppContextValue>(
    () => ({ ...state, setLanguage, setKioskLocation, login, logout }),
    [state, setLanguage, setKioskLocation, login, logout],
  )

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
