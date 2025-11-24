const sliderValues = {};

function updateSlider(sliderName, slideAmount) {
    // Store the slider value in the dictionary
    sliderValues[sliderName] = slideAmount;
}

// function updateClientQueue() {
//     const sessionId = window.location.pathname.split('/')[1];

//     fetch(`/${sessionId}/update-clientQueue`)
//     .then(response => response.json())
//     .then(data => {
//         if (data.url) {
//             window.location.href = data.url;
//         }
//     })
//     .catch(error => console.error('Error updating client queue:', error));
// }

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('start-modal').classList.add('is-active');

    const form = document.getElementById('preFeedbackForm');
    form.addEventListener('submit', function(e) {
        e.preventDefault(); 
        const formData = new FormData(this);
        const formValues = {};
        formData.forEach((value, key) => { formValues[key] = value; });

        // Check if all emotion regulation questions were answered
        radioKeysValidation = ["emotion_reg_q1", "emotion_reg_q2", "emotion_reg_q3"]
        allKeysExist = radioKeysValidation.every(key => Object.keys(formValues).includes(key));
        if (!allKeysExist){
            alert("Please respond to all questions.");
            return;
        }
        const sessionId = window.location.pathname.split('/')[2];
        const clientParam = window.location.href.split('?')[1];

        data = formValues
        data['client_param'] = clientParam

        console.log('Submitting data:', data);
        console.log('Session ID:', sessionId);
        console.log('URL:', `/store-pre-task-survey/${sessionId}/`);

        fetch(`/store-pre-task-survey/${sessionId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);
            console.log('Response headers:', response.headers.get('content-type'));

            // First get response as text to see what we got
            return response.text().then(text => {
                console.log('Response text:', text.substring(0, 200));

                if (!response.ok) {
                    throw new Error(`Server error (${response.status}): ${text}`);
                }

                // Try to parse as JSON
                try {
                    return JSON.parse(text);
                } catch (e) {
                    throw new Error(`Response is not JSON: ${text.substring(0, 100)}`);
                }
            });
        })
        .then(data => {
            console.log('Success response:', data);
            // Redirect to chat interface
            if (data.next_url) {
                window.location.href = data.next_url;
            } else {
                throw new Error('No next_url in response');
            }
        })
        .catch((error) => {
            console.error('Full error:', error);
            alert('Error submitting feedback: ' + error.message + '\nCheck browser console for details');
        });
    });
});
