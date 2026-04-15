import { Layout, Row, Col } from "antd";

function Footer() {
  const { Footer: AntFooter } = Layout;

  return (
    <AntFooter style={{ background: "#fafafa" }}>
      <Row className="just">
        <Col xs={24} md={12} lg={12}>
          <div className="copyright">
            {/* Updated Text Below */}
            Copyright © {new Date().getFullYear()} Montreal Intl | Designed by{" "}
            <a href="#" className="font-weight-bold" target="_blank" rel="noreferrer">
              Designity
            </a>
          </div>
        </Col>
        <Col xs={24} md={12} lg={12}>
          <div className="footer-menu">
            <ul>
              <li className="nav-item">
                <a
                  href="#"
                  className="nav-link text-muted"
                  target="_blank"
                  rel="noreferrer"
                >
                  Company
                </a>
              </li>
              <li className="nav-item">
                <a
                  href="#"
                  className="nav-link text-muted"
                  target="_blank"
                  rel="noreferrer"
                >
                  About Us
                </a>
              </li>
              <li className="nav-item">
                <a
                  href="#"
                  className="nav-link text-muted"
                  target="_blank"
                  rel="noreferrer"
                >
                  Blog
                </a>
              </li>
              <li className="nav-item">
                <a
                  href="#"
                  className="nav-link pe-0 text-muted"
                  target="_blank"
                  rel="noreferrer"
                >
                  License
                </a>
              </li>
            </ul>
          </div>
        </Col>
      </Row>
    </AntFooter>
  );
}

export default Footer;