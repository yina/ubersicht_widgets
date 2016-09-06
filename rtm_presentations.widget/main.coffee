command: "sleep 15 | /Users/yina/.pyenv/shims/python /Users/yina/Dropbox/Backups/geektool/ubersicht_widgets/bin/rtm_cli.py -c -p ls list:sl_presentations priority:1"

refreshFrequency: 10000

style: """
  top: 450px
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
		padding 10px
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
     PRESENTATIONS-MEETINGS-TEACHING
     </thead>
					<tbody>
						<tr>
       #{output}
						</tr>
					</tbody>
				</table>
			</li>
   </ul>
</div>
"""
