import { connect } from 'react-redux';
import App from '../components/App';
import { setLanguage } from '../actions/lang.action';


const mapStateToProps = (state, ownProps) => {
    //console.log("App", "mapStateToProps", state, state.lang.language);
    return {
        language : state.lang.language,
    };
};

const mapDispatchToProps = (dispatch, ownProps) => ({
    setLanguage: (lang) => dispatch(setLanguage(lang)),
});

export default connect(
    mapStateToProps,
    mapDispatchToProps,
    null,
    {
        forwardRef: true,
    }
)(App);
