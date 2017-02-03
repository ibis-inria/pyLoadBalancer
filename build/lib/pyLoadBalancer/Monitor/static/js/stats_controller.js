var ChartInit = false,
    TotalTasksData = {}, TotalTasks = 0, TotalCalcTimesData = {}, TotalCalcTime = 0,
    WaitTimesData = {},MinWaitTime = 1e10,MeanWaitTime = 0,MaxWaitTime = 0,
    CalcTimesData = {},MinCalcTime = 1e10,MeanCalcTime = 0,MaxCalcTime = 0,
    ChartTotalTasks,ChartTotalCalcTimes,ChartWaitTimes,ChartCalcTimes;


function initCharts(){
  $("#chartcalctimes").attr('width',20*rem());
  $("#chartcalctimes").attr('height',20*rem());
  $("#charttotaltasks").attr('width',12*rem());
  $("#charttotaltasks").attr('height',12*rem());
  $("#charttotalcalctimes").attr('width',12*rem());
  $("#charttotalcalctimes").attr('height',12*rem());
  $("#chartwaittimes").attr('width',20*rem());
  $("#chartwaittimes").attr('height',20*rem());

  ChartTotalTasks = new Chart($("#charttotaltasks"), {
     type: 'pie',
     data: TotalTasksData,
     options: {
       responsive: false,
       legend: {display:false}
     }
  });
  ChartTotalCalcTimes = new Chart($("#charttotalcalctimes"), {
     type: 'pie',
     data: TotalCalcTimesData,
     options: {
       responsive: false,
       legend: {display:false}
     }
  });
  ChartWaitTimes = new Chart($("#chartwaittimes"), {
     type: 'radar',
     data: WaitTimesData,
     options: {
       responsive: false,
       scale: {reverse: true},
       //scale: {}
     }
  });
  ChartCalcTimes = new Chart($("#chartcalctimes"), {
     type: 'radar',
     data: CalcTimesData,
     options: {
       responsive: false,
       scale: {reverse: true}
     }
  });
}

function refreshStats(){

  var dataToSend = JSON.stringify({iwouldlike: "STATS",});
  $.ajax(
          {
              url: window.location.href+'jsontoLB/',
              type: 'POST',
              data: dataToSend,
              contentType: 'application/json',
              dataType: 'json',

              success: function (result) {
                console.log("command stats success",result);
                if (result != 0) {
                  console.log("STATS",result);
                  TotalTasksData = {labels: [], datasets: [{data: [],backgroundColor:[],hoverBackgroundColor: [] }]  };
                  TotalCalcTimesData = {labels: [], datasets: [{data: [],backgroundColor:[],hoverBackgroundColor: [] }]  };
                  WaitTimesData = {labels: [], datasets: [
                    {label: "Max queuing time",backgroundColor: 'rgba(255,255,255,0)',borderColor: TRANSPCOLORS[2],pointBackgroundColor: TRANSPCOLORS[2],pointBorderColor: COLORS[2],pointHoverBackgroundColor: COLORS[2],pointHoverBorderColor: COLORS[2],data: []},
                    {label: "Mean queuing time",backgroundColor: 'rgba(255,255,255,0)',borderColor: TRANSPCOLORS[0],pointBackgroundColor: TRANSPCOLORS[0],pointBorderColor: COLORS[0],pointHoverBackgroundColor: COLORS[0],pointHoverBorderColor: COLORS[0],data: []},
                    {label: "Min queuing time",backgroundColor: 'rgba(255,255,255,0)',borderColor: TRANSPCOLORS[1],pointBackgroundColor: TRANSPCOLORS[1],pointBorderColor: COLORS[1],pointHoverBackgroundColor: COLORS[1],pointHoverBorderColor: COLORS[1],data: []},
                  ]};
                  CalcTimesData = {labels: [], datasets: [
                    {label: "Max computing time",backgroundColor: 'rgba(255,255,255,0)',borderColor: TRANSPCOLORS[2],pointBackgroundColor: TRANSPCOLORS[2],pointBorderColor: COLORS[2],pointHoverBackgroundColor: COLORS[2],pointHoverBorderColor: COLORS[2],data: []},
                    {label: "Mean computing time",backgroundColor: 'rgba(255,255,255,0)',borderColor: TRANSPCOLORS[0],pointBackgroundColor: TRANSPCOLORS[0],pointBorderColor: COLORS[0],pointHoverBackgroundColor: COLORS[0],pointHoverBorderColor: COLORS[0],data: []},
                    {label: "Min computing time",backgroundColor: 'rgba(255,255,255,0)',borderColor: TRANSPCOLORS[1],pointBackgroundColor: TRANSPCOLORS[1],pointBorderColor: COLORS[1],pointHoverBackgroundColor: COLORS[1],pointHoverBorderColor: COLORS[1],data: []},
                  ]};


                  icolor = 0;
                  TotalTasks = 0;
                  TotalCalcTime = 0;
                  if (ChartInit == false){
                    $('#globalstatslegend').empty();
                  }

                  for (var command in result){
                    TotalTasksData["labels"].push(command);
                    TotalCalcTimesData["labels"].push(command);
                    WaitTimesData["labels"].push(command);
                    CalcTimesData["labels"].push(command);

                    TotalTasksData["datasets"][0]["data"].push(result[command]["totaltasks"]);
                    TotalTasksData["datasets"][0]["backgroundColor"].push(COLORS[icolor]);
                    TotalTasksData["datasets"][0]["hoverBackgroundColor"].push(TRANSPCOLORS[icolor]);

                    TotalCalcTimesData["datasets"][0]["data"].push(result[command]["totalcalctimes"].toFixed(1));
                    TotalCalcTimesData["datasets"][0]["backgroundColor"].push(COLORS[icolor]);
                    TotalCalcTimesData["datasets"][0]["hoverBackgroundColor"].push(TRANSPCOLORS[icolor]);

                    WaitTimesData["datasets"][2]["data"].push(result[command]["minwaittimes"].toPrecision(2));
                    WaitTimesData["datasets"][1]["data"].push(result[command]["meanwaittimes"].toPrecision(2));
                    WaitTimesData["datasets"][0]["data"].push(result[command]["maxwaittimes"].toPrecision(2));

                    CalcTimesData["datasets"][2]["data"].push(result[command]["mincalctimes"].toPrecision(2));
                    CalcTimesData["datasets"][1]["data"].push(result[command]["meancalctimes"].toPrecision(2));
                    CalcTimesData["datasets"][0]["data"].push(result[command]["maxcalctimes"].toPrecision(2));

                    TotalTasks += result[command]["totaltasks"];
                    TotalCalcTime += result[command]["totalcalctimes"];

                    MinWaitTime = Math.min(MinWaitTime,result[command]["minwaittimes"]);
                    MeanWaitTime += result[command]["totaltasks"] * result[command]["meanwaittimes"];
                    MaxWaitTime = Math.max(MaxWaitTime,result[command]["maxwaittimes"]);

                    MinCalcTime = Math.min(MinCalcTime,result[command]["mincalctimes"]);
                    MeanCalcTime += result[command]["totaltasks"] * result[command]["meancalctimes"];
                    MaxCalcTime = Math.max(MaxCalcTime,result[command]["maxcalctimes"]);

                    if (ChartInit == false){
                      $('#globalstatslegend').append('<div style="display:inline-block"><div class="legendblock" style="background-color:'+COLORS[icolor]+';">&nbsp;</div> '+command+'</div>');
                    }
                    icolor++;
                  }

                MeanWaitTime /= TotalTasks;
                MeanCalcTime /= TotalTasks;

                if (ChartInit == false){
                  initCharts();
                  ChartInit = true;
                }
                refreshTotalTasks();
                refreshTotalCalcTimes();
                refreshWaitTimes();
                refreshCalcTimes();

                }
              },
              error: function () {
                console.log("Command Info : Error loading JSON data");
              },
              complete: function() {
                console.log("command info complete");
              }
          });
}

function refreshTotalTasks(){
  $("#totaltasks").text(TotalTasks);

  ChartTotalTasks.data.datasets = TotalTasksData["datasets"];
  ChartTotalTasks.update(0);

}

function refreshTotalCalcTimes(){
  $("#totalcalctimes").text(TotalCalcTime.toFixed(1));

  ChartTotalCalcTimes.data.datasets = TotalCalcTimesData["datasets"];
  ChartTotalCalcTimes.update(0);
}

function refreshWaitTimes(){
  $("#minwaittime").text(MinWaitTime.toPrecision(2));
  $("#meanwaittime").text(MeanWaitTime.toFixed(2));
  $("#maxwaittime").text(MaxWaitTime.toFixed(2));

  ChartWaitTimes.data.datasets = WaitTimesData["datasets"];
  ChartWaitTimes.updateDatasets();
}

function refreshCalcTimes(){
  $("#mincalctime").text(MinCalcTime.toPrecision(2));
  $("#meancalctime").text(MeanCalcTime.toFixed(2));
  $("#maxcalctime").text(MaxCalcTime.toFixed(2));

  ChartCalcTimes.data.datasets = CalcTimesData["datasets"];
  ChartCalcTimes.update(0);
}
