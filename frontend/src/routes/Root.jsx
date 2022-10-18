import React from 'react'
import { Container } from 'react-bootstrap'
import { Outlet } from 'react-router-dom'
import Footer from '../components/UI/Footer'
import MyNavbar from '../components/UI/MyNavbar'

const Root = () => {
  return (
    <Container>
      <MyNavbar />
      <div id="detail">
        <Outlet />
      </div>
      <Footer className="justify-content-end"/>
    </Container>

  )
}

export default Root
