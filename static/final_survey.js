// sessionId and treatmentGroup are defined in the HTML template
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('final-survey-modal').classList.add('is-active');

    const form = document.getElementById('finalSurveyForm');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Collect form data
        const formData = new FormData(this);
        const data = {};
        formData.forEach((value, key) => { data[key] = value; });

        // Define required fields based on treatment group
        let requiredFields = [
            'surface_act', 'surface_mask', 'surface_fake',
            'deep_experience', 'deep_effort', 'deep_work',
            'natural_genuine', 'natural_come_naturally', 'natural_spontaneous',
            'burnout_frustrating', 'burnout_drain', 'burnout_tired',
            'satisfaction', 'recovery'
        ];

        // Add AI-related fields if treatment group has AI
        if (treatmentGroup === 'information' || treatmentGroup === 'emotion' || treatmentGroup === 'both') {
            requiredFields = requiredFields.concat([
                'advice_helpful', 'advice_supportive', 'advice_informative', 'advice_compassionate',
                'usefulness_quickly', 'usefulness_performance', 'usefulness_useful',
                'trust_guidance', 'trust_rely', 'trust_dependable',
                'literacy_evaluate', 'literacy_choose', 'literacy_appropriate'
            ]);
        }

        // Validate all required questions answered
        for (const field of requiredFields) {
            if (!data[field]) {
                alert('Please answer all questions before continuing.');
                return;
            }
        }

        // Submit to backend
        try {
            const response = await fetch(`/store-final-survey/${sessionId}/`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });

            if (response.ok) {
                const result = await response.json();
                // Redirect to complete page
                window.location.href = result.next_url;
            } else {
                alert('Error saving survey. Please try again.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Network error. Please check your connection.');
        }
    });
});
