import React from 'react';
import { Row } from 'react-bootstrap';
import { Link } from 'react-router-dom';

const Footer = () => {
    return (
        <Row className="align-items-end">
            <Link to={`about`}>about</Link>
        </Row>
    );
};

export default Footer;