command: "sleep 10 | /Users/yina/.pyenv/shims/python /Users/yina/Dropbox/Backups/geektool/ubersicht_widgets/bin/rtm_cli.py -c -p ls list:.events_travel"

refreshFrequency: false

style: """
  top: 100px
  left: 750px

	*
		margin 0
		padding 0

	#container1
		margin 0
		padding 0
		color rgba(#fff, .9)
		font-family Lucida Grande
		font-size 10pt

	ul
		list-style none

	li
		padding 0px
		&:not(:last-child)
			border-bottom solid 1px white

	tbody
		font-size 12pt

  td
  	width 60px
   text-align right

"""

render: (output) -> """
<div id="container1">
  <ul>
  <li>
				<table>
    <thead>
    EVENTS TRAVEL
    </thead>
					<tbody>
       #{output}
					</tbody>
				</table>
			</li>
   </ul>
</div>
"""
