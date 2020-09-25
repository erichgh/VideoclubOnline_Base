function fetchdata(){
    $.ajax({
        url: '/people',
        type: 'get',
        success: function(response){
            // Perform operation on the return value
            $('#people').text(response);
        }
    });
}

$(document).ready(function(){
    fetchdata();
    setInterval(fetchdata,3000);
});