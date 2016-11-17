var InitQueueChart = false;
var queueData = [];
var queueChart = null;
var currentcolori = 0;

function refreshWorkers() {
  var dataToSend = JSON.stringify({iwouldlike: "WORKERS",});
  $.ajax(
          {
              url: window.location.href+'jsontoLB/',
              type: 'POST',
              data: dataToSend,
              contentType: 'application/json',
              dataType: 'json',

              success: function (result) {
                console.log("command workers success",result);

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

                refreshQueueChart(result.commandqueue);

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

function refreshQueueChart(queueData) {
  if (InitQueueChart == false){
    InitQueueChart = true;

    $("#chartqueuecommand").attr('width',30*rem());
    $("#chartqueuecommand").attr('height',20*rem());
    $("#chartqueuetime").attr('width',30*rem());
    $("#chartqueuetime").attr('height',20*rem());

    queueChart = new Chart($("#chartqueuecommand"), {
          type: 'line',
          data: {datasets: [{label:'Total', data:[], fill:false,
                            borderColor:'rgba(0,0,0,0.3)',pointRadius:0,lineTension:0}]},
          options: {
            responsive: false,
            animation: {duration:0},
            scales: {
                xAxes: [{
                    type: 'linear',
                    ticks: {
                        callback: function(value) {
                            return new Date(value).toTimeString().replace(/.*(\d{2}:\d{2}:\d{2}).*/, "$1");
                        },
                    },
                    position: 'bottom'
                }],
                yAxes: [{
                    type: 'linear',
                    scaleLabel: {display:true, labelString:'Queuing Tasks' },
                    ticks: {
                        min:0
                    }
                }]
            }
          }
      });

      queueTimeChart = new Chart($("#chartqueuetime"), {
            type: 'line',
            data: {datasets: []},
            options: {
              responsive: false,
              animation: {duration:0},
              scales: {
                  xAxes: [{
                      type: 'linear',
                      ticks: {
                          callback: function(value) {
                              return new Date(value).toTimeString().replace(/.*(\d{2}:\d{2}:\d{2}).*/, "$1");
                          }
                      },
                      position: 'bottom'
                  }],
                  yAxes: [{
                      type: 'linear',
                      scaleLabel: {display:true, labelString:'Time (s)' },
                      ticks: {
                          min:0
                      }
                  }]
              }
            }
        });


  }

  var currentTime = new Date();

  for (var command in queueData){
    newcommand = true;
    queueChart.data.datasets.forEach(function(dataset, index) {
      if (dataset.label == command){
        newcommand = false;
      }
    });
    if (newcommand){
      console.log('adding command',command, currentcolori);
      queueChart.data.datasets.push({label:command, data:[], fill:false,
                                      borderColor:VERYLIGHTCOLORS[currentcolori],pointRadius:0,lineTension:0});
      queueTimeChart.data.datasets.push({label:command, data:[], fill:false,
                                      borderColor:VERYLIGHTCOLORS[currentcolori], pointRadius:0,lineTension:0});
      currentcolori++;
    }
  }


  var total = 0;
  queueChart.data.datasets.forEach(function(dataset, index) {
    var valuefound = false;
    for (var command in queueData){
      if (dataset.label == command){
        dataset.data.push( {x:currentTime,y:queueData[command]['number']} );
        total += queueData[command]['number'];
        valuefound = true;
      }
    }
    if (valuefound == false && dataset.label != 'Total'){
      dataset.data.push( {x:currentTime,y:0} );
    }
    if ((dataset.data.length > 0) &&(currentTime - dataset.data[0].x > 60000)) {
      dataset.data.splice(0,1);
    }
  });
  $("#totalqueingtasks").text(total.toFixed(0));
  queueChart.data.datasets[0].data.push( {x:currentTime,y:total} );
  queueChart.update();

  var maxtime=0;
  queueTimeChart.data.datasets.forEach(function(dataset, index) {
    var valuefound = false;
    for (var command in queueData){
      if (dataset.label == command){
        dataset.data.push( {x:currentTime,y:queueData[command]['waitingtime']} );
        maxtime = Math.max(maxtime,queueData[command]['waitingtime'])
        valuefound = true;
      }
    }
    if (valuefound == false){
      dataset.data.push( {x:currentTime,y:0} );
    }
    if (currentTime - dataset.data[0].x > 60000) {
      dataset.data.splice(0,1);
    }
  });
  $("#totalqueingtasks").text(maxtime.toFixed(0));
  queueTimeChart.update();


}
