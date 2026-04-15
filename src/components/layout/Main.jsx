import { useState } from "react";
import { useLocation, Outlet, Navigate } from "react-router-dom";
import { Layout, Drawer, Affix } from "antd";
import Sidebar from "../Sidebar";
import Header from "./Header";
import Footer from "./Footer";
import { useAuth } from "../../context/AuthContext";
import "../../assets/styles/main.css";
import "../../assets/styles/responsive.css";

const { Header: AntHeader, Content, Sider } = Layout;

function Main() {
  const { isAuthenticated } = useAuth();
  const [visible, setVisible] = useState(false);
  const [sidenavColor, setSidenavColor] = useState("#1890ff");
  const [fixed, setFixed] = useState(false);

  const openDrawer = () => setVisible(!visible);
  
  let { pathname } = useLocation();
  pathname = pathname.replace("/", "");

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <>
      <style>
        {`
          .layout-content-wrapper {
            margin-left: 0px;
            transition: all 0.2s;
          }
          @media (min-width: 992px) {
            .layout-content-wrapper {
              margin-left: 250px !important; 
            }
          }
        `}
      </style>

      <Layout className="layout-dashboard">
        {/* 
           MOBILE SIDEBAR (Drawer)
           FIX: Removed 'width={250}' prop.
           Added 'wrapper: { width: 250 }' inside styles prop.
        */}
        <Drawer
          title={null}
          placement="left"
          closable={false}
          onClose={() => setVisible(false)}
          open={visible}
          key="left-drawer"
          className="drawer-sidebar"
          styles={{ 
            body: { padding: 0 }, 
            wrapper: { width: 250 } // <--- Moved width here to fix warning
          }}
        >
          <Layout className="layout-dashboard" style={{ background: "white", height: "100%" }}>
            <Sider 
              trigger={null} 
              width={250} 
              theme="light" 
              className="sider-primary ant-layout-sider-primary"
            >
              <Sidebar />
            </Sider>
          </Layout>
        </Drawer>

        {/* DESKTOP SIDEBAR (Fixed) */}
        <Sider
          breakpoint="lg"
          collapsedWidth="0"
          onCollapse={(collapsed, type) => { console.log(collapsed, type); }}
          trigger={null}
          width={250}
          theme="light"
          className="sider-primary ant-layout-sider-primary"
          style={{
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 999,
            height: '100vh',
            overflowY: 'auto'
          }}
        >
          <Sidebar />
        </Sider>

        {/* MAIN CONTENT AREA */}
        <Layout className="layout-content-wrapper">
          {fixed ? (
            <Affix>
              <AntHeader className="ant-header-fixed">
                <Header
                  onPress={openDrawer}
                  name={pathname}
                  subName={pathname}
                  handleSidenavColor={setSidenavColor}
                  handleFixedNavbar={setFixed}
                />
              </AntHeader>
            </Affix>
          ) : (
            <AntHeader style={{ background: "transparent" }}>
              <Header
                onPress={openDrawer}
                name={pathname}
                subName={pathname}
                handleSidenavColor={setSidenavColor}
                handleFixedNavbar={setFixed}
              />
            </AntHeader>
          )}
          
          <Content className="content-ant" style={{ overflowX: "hidden" }}>
              <Outlet /> 
          </Content>
          
          <Footer />
        </Layout>
      </Layout>
    </>
  );
}

export default Main;