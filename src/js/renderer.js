//const binder = require('./index');
//const ipcRenderer=window.BinderApi.ipc
//const { ipcRenderer } = require('electron');


window.addEventListener('DOMContentLoaded', () => {
    // Your initialization code goes here
    
    // Example: Call Python function when a button is clicked
    const openFileButton = document.getElementById('out');
    openFileButton.addEventListener('click', () => {
        const path = 'hello world';
        window.BinderApi.openFile(path);
    });
    
});


function say(data){
    document.getElementById('hput').textContent = data;
}

window.BinderApi.outt((message) => {
    say(message)
});
  