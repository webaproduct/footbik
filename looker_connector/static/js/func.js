function copyToClipboard(id){
               alert("sex")

            var copyText = document.getElementsByName(id);
            copyText.parentNode.lastChild.innerText = "Copied!"

        // Select the text field
        copyText.select();
        copyText.setSelectionRange(0, 99999); // For mobile devices

        // Copy the text inside the text field
        navigator.clipboard.writeText(copyText.value);
        }



