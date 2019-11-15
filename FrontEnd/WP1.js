// Please replace the YOUR_API_ENDPOINT_URL with yours
// Please replace the apigClient with yours

let apigClient = apigClientFactory.newClient({
    apiKey : 'Your API Key'
});

var headerParams = {
    //This is where any header, path, or querystring request params go. The key is the parameter named as defined in the API
    "Content-type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "x-api-key": "Your API Key",
    "Access-Control-Allow-Credentials" : "true", 
    "Access-Control-Allow-Methods" : "GET,HEAD,OPTIONS,POST,PUT",
    "Access-Control-Allow-Headers" : "*"
};


// Add listeners for submit button that make the API request
document.getElementById('submitButton').addEventListener('click', function(e) {
    sendDataToApi(e);
});

// Add listeners for pressing ENTER in keyboard
// (document).keydown(function(event){
    // if(event.keyCode == 13){
        // $("#submitButton").click();
    // //}
// });

// Setup easy way to get the reference values from both Input and URL
var errorDiv = document.getElementById('error-message');
function nameValue() { return (String(document.getElementById('firstName').value)  + " " + String(document.getElementById('lastName').value)); }
function phoneNumberValue() {return String(document.getElementById('phoneNumber').value);}
function faceIdValue() {return document.getElementById('faceId').value;}
function objectKeyValue() {return document.getElementById('objectKey').value;}
function bucketValue() {return document.getElementById('bucket').value;}
function createdTimestampValue() {return document.getElementById('createdTimestamp').value;}
function checkedBoxValue() {return document.getElementById("denyAccess").checked;}



// Prepare to send data
function sendDataToApi(e){
    //e.preventDefault()
    //let inputQuery = messageValue();
    //callApi({ "message": inputQuery });
    var checked;
    if (checkedBoxValue() == true) {
        checked = 1;
    }else {
        checked = 0;
    }
    callApi({"faceId" : faceIdValue(), "name" : nameValue(), "phoneNumber" : phoneNumberValue(), "objectKey" : objectKeyValue(), "bucket" : bucketValue(), "createdTimestamp" : createdTimestampValue(), "checked" : String(checked)});
    var firstNameInputBox = document.getElementById("firstName");
    var lastNameInputBox = document.getElementById("lastName");
    var phoneNumberInputBox = document.getElementById("phoneNumber");
    firstNameInputBox.value = ""; firstNameInputBox.textContent = '';
    lastNameInputBox.value = ""; lastNameInputBox.textContent = '';
    phoneNumberInputBox.value = ""; phoneNumberInputBox.textContent = '';
    document.getElementById("denyAccess").checked = false;
}

// Send HTTP POST request to AWS Gateway
function callApi(info) {
    //alert(info.name + info.phoneNumber+ info.checked);
    apigClient.addvisitorPost(headerParams, info, {})
        .then(function(result) {
            console.log(result);
            alert((result.data));
            //let msg = { "query" : query.message, "response" : result.data }
            //messagesArray.push(msg)
            //render();
            //resultsDiv.textContent = JSON.stringify(result.data);
        })
        .catch(function(err) {
            errorDiv.textContent = 'Failed! There was an error:\n' + err.toString();
        });
}


