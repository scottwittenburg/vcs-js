var canvas;
var renderer;
var boxfill;
var variables;

function vcs_boxfill_close()
{
  canvas.close();
}

function vcs_boxfill_clear()
{
  canvas.clear();
}

function vcs_plot_mycolormap(evt) {
  function applyMagmaColorsToMyMap(colorMapNotUsed) {
    vcs.getcolormap('magma').then((magmaCm) => {
      vcs.setcolormap('mycolormap', magmaCm).then(() => {
        boxfill.colormap = 'mycolormap';
        var rendererPromise = canvas.plot(variables.clt, boxfill);
        rendererPromise.then((r) => {
          renderer = r;
          renderer.onImageReady(() => {
            console.log('Ready magma');
          });
        });
      });
    });
  }

  vcs.getcolormap('mycolormap').then(applyMagmaColorsToMyMap, (cmErr) => {
    // Didn't have "mycolormap" yet, so we'll create it
    vcs.createcolormap('mycolormap').then(applyMagmaColorsToMyMap);
  });
}


function vcs_boxfill_resize()
{
  canvas.resize(600, 400);
  console.log('div resize');
}

$(function () {
  variables = {
    "clt": {"uri": "clt.nc", "variable": "clt"},
  }

  canvas = vcs.init(document.getElementById('vcs-boxfill'));
  vcs.creategraphicsmethod('boxfill', 'myboxfill').then((gm) => {
    boxfill = gm;
    return canvas.plot(variables.clt, ['boxfill', 'myboxfill']);
  }).then((r) => {
    renderer = r;
    renderer.onImageReady(() => {
      console.log("Ready1");
    });
  });
});
