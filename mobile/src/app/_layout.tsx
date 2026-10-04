import {Stack} from 'expo-router';
import {StatusBar} from 'expo-status-bar';
import {SessionProvider} from '../lib/session';
import {color} from '../lib/ui';
export default function Layout(){return <SessionProvider><StatusBar style="light"/><Stack screenOptions={{headerStyle:{backgroundColor:color.bg},headerTintColor:color.text,contentStyle:{backgroundColor:color.bg}}}><Stack.Screen name="(tabs)" options={{headerShown:false}}/><Stack.Screen name="welcome" options={{title:'欢迎来到沪漂树洞',headerBackVisible:false}}/><Stack.Screen name="post/[id]" options={{title:'匿名讨论'}}/><Stack.Screen name="moderation" options={{title:'我的审核记录'}}/><Stack.Screen name="guide" options={{title:'新手指南'}}/><Stack.Screen name="rules" options={{title:'社区与隐私'}}/></Stack></SessionProvider>}
