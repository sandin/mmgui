import React from 'react';
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import { Layout, Button } from 'antd';

import './App.css';

const { Header, Footer, Sider, Content } = Layout;

/**
 * App
 */
export default class App extends React.Component {

    constructor(props) {
        super(props);
    }

    render() {
        console.log("App", "render", this.props);
        return (
            <Layout style={{width: "100%", height: "100%"}}>
              <Header>Header</Header>
              <Content>
                {this.props.language == "zh-cn" && (
                     <h1>你好, React!</h1>
                 )}
                 {this.props.language == "en" && (
                     <h1>Hello, React!</h1>
                 )}

                 <div>Language:
                     <Button disabled={this.props.language == "zh-cn"} onClick={() => this.props.setLanguage("zh-cn")}>中文</Button>
                     <Button disabled={this.props.language == "en"} onClick={() => this.props.setLanguage("en")}>English</Button>
                 </div>
              </Content>
              <Footer>Footer</Footer>
            </Layout>
        );
    }

}
