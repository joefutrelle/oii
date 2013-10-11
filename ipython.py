import uuid
from IPython.display import HTML, Javascript, display

pb_html = """
<div style="border: 1px solid black; width:500px">
  <div id="%s" style="background-color:orange; width:0%%">&nbsp;</div>
</div>
"""

class ProgressBar(object):
    def __init__(self):
        self.divid = str(uuid.uuid4())
        display(HTML(pb_html % self.divid))
    def progress(self,i,n=100):
        pct = int(100.0 * i / n)
        display(Javascript("$('div#%s').width('%i%%')" % (self.divid, pct)))
