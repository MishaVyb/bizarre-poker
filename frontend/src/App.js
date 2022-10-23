import './../node_modules/bootswatch/dist/sketchy/bootstrap.css'
import React from 'react'

import { AuthContext, ErrorContext } from './context'
import { useEffect, useMemo, useState } from 'react'
import { getRouter } from './routes/Router'
import { RouterProvider } from 'react-router-dom'
import AuthService from './services/AuthService'
import GameService from './services/GameService'
import ErrorToast from './components/UI/ErrorToast'

function App() {

  // global auth state // setAuth will make changes to services and router also
  const [auth, setAuth] = useState({isLoading: true})
  const [error, setErrorState] = useState(null)

  const setError = (error) => {
    setErrorState(error)
    setTimeout(()=>{setErrorState(null)}, 5000)
  }

  // memo 1 -- services
  const services = useMemo(() => {
    return {
      authService: new AuthService(auth?.token),
      gameService: new GameService(auth?.token),
    }
  }, [auth])

  // memo 2 -- router
  const router = useMemo(() => {return getRouter(services.authService, services.gameService)
  }, [services])

  // on mount -- load auth from local storage
  // it will make effect on memo-1 and memo-2
  useEffect(() => {
    if (localStorage.getItem('token')) {
      const loadedAuth = {
        username: localStorage.getItem('username'),
        token: localStorage['token'],
      }

      ////////////////// extra //////////////////////////
      // load user detail in background (no waiting)
      const service = new AuthService(loadedAuth.token)
      service.me().then((userDetatil) => {
        console.log('info : get `me` at App mounting sucessfuly')
        loadedAuth.user = userDetatil
        setAuth(loadedAuth)

      }).catch((error)=>{
        console.log('error : get `me` failed', error)
      })
      ////////////////////////////////////////////////

      setAuth(loadedAuth)
    } else {
      setAuth(null)
    }
  }, []) // no dependencis, only at first component mount

  return (
    <div className="App">
      <AuthContext.Provider value={{ auth, setAuth, ...services}}>
        <ErrorContext.Provider value={{error, setError}}>
          <RouterProvider router={router} />
        </ErrorContext.Provider>
      </AuthContext.Provider>

    </div>
  )
}

export default App
