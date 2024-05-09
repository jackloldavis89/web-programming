//where to mount the vue app
mountSelector = '';

//vue app
const app = Vue.createApp({
    data() {
        return {
            display: false,
        }
    },
    methods: {
        formDisplay(e) {
            this.display = !this.display;
            //console.log(this.display);
        },
    },
    delimiters : ['[[', ']]'], // Used to bypass flask's jinja2 delimiters
}).mount("#v-add-form");

toggleEdit = (id) => {
    document.getElementById(`edit-${id}`).classList.toggle('d-none');
}

accessEdit = (radio) => {
    console.log(radio);
}

toggleComments = (id) => {
    let comments = document.getElementById(`comments-${id}`)
    comments.classList.toggle('d-none');
    if(comments.classList.contains('d-none')){
        comments.parentElement.children[4].innerHTML = '<i class="material-icons icon-align">expand_more</i>' 
    } else {
        comments.parentElement.children[4].innerHTML = '<i class="material-icons icon-align">expand_less</i>' 
    }
    
    console.log(comments);

}

setAccess = (id, access) => {
    let edit = document.getElementById(`edit-${id}`);
    let access_hidden = edit.children[0].children[6];
    access_hidden.value = access;
}


