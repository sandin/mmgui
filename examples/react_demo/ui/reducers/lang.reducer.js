import { SET_LANGUAGE } from '../actions/lang.action';

const initialState = {
    language: "en",
};

const reducer = (state = initialState, action) => {
    //console.log("lang.reducer", "action", action, "state", state);
    switch (action.type) {
        case SET_LANGUAGE:
            //window.location.reload();
            return {
                ...state,
                language: action.language
            };
        default:
            return state;
    }
};

export default reducer;
