function start_equals_end() {
    return document.querySelector("#checkbox_start_is_stop").checked;
}

function get_ajax_headers(jwt) {
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + String(jwt)
    }
}

function parse_place_card(place_card) {
    var input_data = {};
    $(place_card).find("input").each(function() {
        input_data[String($(this).attr("name"))] = $(this).val();
    });
    return input_data;
}

async function process_route() {
    $("input, button").each(function() {
        $(this).prop('disabled', true);
    });

    try {
        var jwt = $("#jwt").attr("value");
        location_data = {
            'start_address': null,
            'intermediate_addresses': [],
            'end_address': null
        }

        // Create the JSON payload for the server to process.
        location_data['start_address'] = parse_place_card($("#form_places_start .place-card"));
        $("#intermediate_stops .place-card").each(function() {
            location_data['intermediate_addresses'].push(parse_place_card($(this)));
        });
        if (start_equals_end()) {
            location_data['end_address'] = location_data['start_address'];
        }
        else {
            $("#form_places_end .place-card")
            location_data['end_address'] = parse_place_card($("#form_places_end .place-card"));
        }

        // Show the alert modal to the user so they know to wait.
        $("#alert_modal .modal-title").html("Planning Route");
        $("#alert_modal .modal-body").html(`
            <p class="lead fw-normal">Your request has been sent to the server for processing. When finished, you should automatically be redirected to see the results.</p>
            <p class="lead fw-normal">This may take up to a few minutes.</p>
            <div class="mt-3 row justify-content-center">
                <div class="col-auto">
                    <div class="spinner-border text-success" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
        `);
        $("#alert_modal .modal-footer .btn").removeAttr("disabled");  // Undo the automatic disabling of the button.
        $("#alert_modal.modal").modal("show");

        // Send the data to the server for processing.
        server_result = await fetch(
            '/api/generate_route/',
            {
                method: 'POST',  // Cannot send JSON data in the body with GET.
                headers: get_ajax_headers(jwt),
                body: JSON.stringify(location_data)
            }
        ).then(response => response.json())
        .catch(error => console.log(error));

        if ('notRoutableException' in server_result) {
            // alert("The server could not route those addresses. This may be because they cannot be connected via roads.")
            // $("#alert_modal.modal").modal("hide");
            $("#alert_modal .modal-title").html("Unable to Route Addresses");
            $("#alert_modal .modal-body").html(`
                <p class="lead fw-normal">Unfortunately, we were unable to route the addresses you provided.</p>
                <p class="lead fw-normal">This might be because they cannot be connected via roads. If your addresses are located in multiple countries, this may be the issue.</p>
                <p class="lead fw-normal">If you believe this is not the problem and continue to experience this error, please feel free to let us know using our <a href="/contact/" target="_blank" rel="noopener noreferrer">contact page</a> and try again later.
            `);
            $("#alert_modal .modal-footer .btn").removeAttr("disabled");  // Undo the automatic disabling of the button.
            $("#alert_modal.modal").modal("show");
        }
        else if ('errors' in server_result || 'error' in server_result) {
            window.location.reload();
        }
        else {
            // Redirect to the route page.
            window.location = server_result['route_url'];
        }
    }
    catch (error) {
        alert(error);
    }
    finally {
        $("input, button").each(function() {
            $(this).prop('disabled', false);
        });

        // Change end card inputs to what they are supposed to be.
        start_checkbutton_changed();
    }
}

$(document).ready(function() {
    $("#routing_form").on('submit', async function (e) {
        // Prevent the page from reloading.
        // This process should be done in pieces via jQuery and JavaScript.
        e.preventDefault();

        // Process the form data.
        await process_route();
    });
    start_checkbutton_changed();
});

