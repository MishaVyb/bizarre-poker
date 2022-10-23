import React, { useContext } from 'react'
import { Container } from 'react-bootstrap'
import { Outlet } from 'react-router-dom'
import ErrorToast from '../components/UI/ErrorToast'
import Footer from '../components/UI/Footer'
import MyNavbar from '../components/UI/MyNavbar'
import { AuthContext, ErrorContext } from '../context'

const Root = () => {
  const {error} = useContext(ErrorContext)

  return (
    <Container>
      <ErrorToast error={error}/>

      <MyNavbar />
      <div id="detail">

        <Outlet />
      </div>
      <Footer className="justify-content-end"/>
    </Container>

  )
}

export default Root


