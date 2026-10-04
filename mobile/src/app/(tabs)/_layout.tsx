import {Tabs,Redirect} from 'expo-router';
import {useSession} from '../../lib/session';
import {color,Loading} from '../../lib/ui';
export default function Layout(){const session=useSession();if(!session.ready)return <Loading/>;if(!session.signedIn)return <Redirect href="/welcome"/>;return <Tabs screenOptions={{headerStyle:{backgroundColor:color.bg},headerTintColor:color.text,tabBarStyle:{backgroundColor:color.card,borderTopColor:color.line},tabBarActiveTintColor:color.accent,tabBarInactiveTintColor:color.muted}}><Tabs.Screen name="index" options={{title:'花园'}}/><Tabs.Screen name="compose" options={{title:'发帖'}}/><Tabs.Screen name="feedback" options={{title:'内测反馈'}}/><Tabs.Screen name="profile" options={{title:'我的'}}/></Tabs>}
