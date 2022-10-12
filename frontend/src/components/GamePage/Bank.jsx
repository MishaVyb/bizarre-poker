import React from 'react'

import { Card, Row } from 'react-bootstrap'

const Bank = ({children}) => {
  return (
    <Row className={'d-flex justify-content-center'} xs={2} md={4} lg={6}>
      <Card md="auto">
        <Card.Title className="mb-2 text-muted">game bank</Card.Title>
        <h1 >{children}</h1>
      </Card>
    </Row>
  )
}

export default Bank