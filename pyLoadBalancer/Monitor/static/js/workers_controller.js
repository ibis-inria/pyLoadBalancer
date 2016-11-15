var InitQueueChart = false;
var queueData = [];
var queueChart = null;
var currentx = 0;

function refreshWorkers() {
  var dataToSend = JSON.stringify({iwouldlike: "WORKERS",});
  $.ajax(
          {
              url: '/jsontoLB/',
              type: 'POST',
              data: dataToSend,
              contentType: 'application/json',
              dataType: 'json',

              success: function (result) {
                //console.log("command workers success",result);

                $('#workerstable').find("tr:gt(0)").remove();
                $.each(result.workers, function (i, worker) {
                    $('<tr>').append(
                    $('<td>').text(worker.workerid),
                    $('<td>').text(worker.workertask),
                    $('<td style="width:10rem">').html('<div class="progresscontainer"><div style="width:'+worker.workerdone+'%; background-color: #90ed7d;">'+worker.workerdone+'</div></div>'),
                    $('<td style="width:10rem">').html('<div class="progresscontainer"><div style="width:'+worker.workerCPU+'%; background-color: #DB3946;">'+worker.workerCPU+'</div></div>'),
                    $('<td>').text(worker.workertaskid),
                    $('<td>').text(worker.workerip),
                    $('<td>').text(worker.workerport),
                    $('<td>').text(worker.workerhealthport),
                    $('<td>').text(worker.workerminpriority),
                    $('<td>').text(worker.workermaxpriority)
                    ).appendTo('#workerstable');
                });

                queueData = result.commandqueue;

                refreshQueueChart();

              },
              error: function () {
                console.log("Error loading Workers JSON data");

              },
              complete: function() {
                  // Schedule the next request when the current one's complete
                  //console.log('COMPLETE')
                  setTimeout(refreshWorkers, 1000);
              }
          });
}

function refreshQueueChart() {
  if (InitQueueChart == false){
    InitQueueChart = true;
    console.log("queueChartData",queueChartData);

    var queueChartData = { datasets: [{label:'no', data: [{x:0,y:0}] }] };
    for (var command in queueData){
      console.log(command);
      queueChartData.datasets.push( {label:command, data: [{x:0,y:queueData[command]['number']}] } );
    }

    queueChart = new Chart($("#chartqueuecommand"), {
          type: 'line',
          data: queueChartData,
          options: {
              scales: {
                  xAxes: [{
                      type: 'linear',
                      position: 'bottom'
                  }]
              }
          }
      });


  }
  else {
    currentx++;
    for (var command in queueData){
      //is command new ?
      newcommand = true;
      queueChart.data.datasets.forEach(function(dataset, index) {
        if (dataset.label == command){
          newcommand = false;
        }
      });
      if (newcommand){
        console.log('adding command',command);
        queueChart.data.datasets.push({label:command, data:[]});
      }
    }

    queueChart.data.datasets.forEach(function(dataset, index) {
      console.log('CHART DATASET',dataset);
      var valuefound = false;
      for (var command in queueData){
        if (dataset.label == command){
          dataset.data.push( {x:currentx,y:queueData[command]['number']} );
          valuefound = true;
        }
      }
      if (valuefound == false){
        dataset.data.push( {x:currentx,y:0} );
      }
    });

    queueChart.update();

  }

}
